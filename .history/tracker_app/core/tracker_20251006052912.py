# ==========================================================
# core/tracker.py (Class-Based Session Tracker)
# ==========================================================

import time
import sqlite3
import json
import pickle
import os
from threading import Event
from datetime import datetime, timedelta
from typing import Dict, Any

from pynput import keyboard, mouse
import win32gui
from plyer import notification
import logging

from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db
from config import DB_PATH, TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL, USER_ALLOW_WEBCAM
from core.ocr_module import ocr_pipeline
from core.audio_module import record_audio, extract_features as audio_extract_features
from core.webcam_module import webcam_pipeline
from core.intent_module import extract_features as intent_extract_features, predict_intent
from core.knowledge_graph import add_concepts, get_graph, add_edges
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve
from core.face_detection_module import FaceDetector

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(filename="logs/tracker.log", level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")

# -----------------------------
# Load classifiers
# -----------------------------
audio_clf_path = "core/audio_classifier.pkl"
audio_clf = None
if os.path.exists(audio_clf_path):
    with open(audio_clf_path, "rb") as f:
        audio_clf = pickle.load(f)
        logging.info("Audio classifier loaded.")

intent_clf_path = "core/intent_classifier.pkl"
intent_map_path = "core/intent_label_map.pkl"
intent_clf = intent_label_map = None
if os.path.exists(intent_clf_path) and os.path.exists(intent_map_path):
    with open(intent_clf_path, "rb") as f:
        intent_clf = pickle.load(f)
    with open(intent_map_path, "rb") as f:
        intent_label_map = pickle.load(f)
    logging.info("Intent classifier loaded.")

# -----------------------------
# SessionData class
# -----------------------------
class SessionData:
    def __init__(self):
        self.window_title: str = ""
        self.interaction_rate: int = 0
        self.ocr_keywords: Dict[str, Any] = {}
        self.audio_label: str = "silence"
        self.audio_confidence: float = 0.0
        self.attention_score: int = 0
        self.intent_label: str = ""
        self.intent_confidence: float = 0.0
        self.start_time: datetime = datetime.now()
        self.last_update: datetime = datetime.now()

        # Internal counters
        self.keyboard_events = 0
        self.mouse_events = 0

    def update_interaction(self):
        self.interaction_rate = self.keyboard_events + self.mouse_events
        self.last_update = datetime.now()

    def reset_events(self):
        self.keyboard_events = 0
        self.mouse_events = 0

# -----------------------------
# Tracker class
# -----------------------------
class Tracker:
    MEMORY_THRESHOLD = 0.6
    REMINDER_COOLDOWN = timedelta(minutes=30)

    def __init__(self, user_allow_webcam: bool = USER_ALLOW_WEBCAM):
        self.session = SessionData()
        self.face_detector = FaceDetector()
        self.user_allow_webcam = user_allow_webcam
        self.G = get_graph()

        # Listeners
        self.kb_listener = keyboard.Listener(on_press=self.on_key_press)
        self.ms_listener = mouse.Listener(on_click=self.on_mouse_click)

        # Timers
        self.counters = {"ocr": 0, "audio": 0, "webcam": 0, "save": 0}

        # Init DB
        init_db()
        init_multi_modal_db()
        init_memory_decay_db()

    # -----------------------------
    # Event handlers
    # -----------------------------
    def on_key_press(self, key):
        self.session.keyboard_events += 1

    def on_mouse_click(self, x, y, button, pressed):
        if pressed:
            self.session.mouse_events += 1

    # -----------------------------
    # Start listeners
    # -----------------------------
    def start_listeners(self):
        self.kb_listener.start()
        self.ms_listener.start()

    # -----------------------------
    # Active window
    # -----------------------------
    def get_active_window(self):
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or "Unknown"
        self.session.window_title = title
        self.session.update_interaction()
        return title, self.session.interaction_rate

    # -----------------------------
    # Logging helpers
    # -----------------------------
    def log_session(self):
        self.session.update_interaction()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        app_name = self.session.window_title.split(" - ")[-1] if " - " in self.session.window_title else self.session.window_title
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                """INSERT INTO sessions 
                (start_ts, end_ts, app_name, window_title, interaction_rate) 
                VALUES (?, ?, ?, ?, ?)""",
                (ts, ts, app_name, self.session.window_title, int(self.session.interaction_rate))
            )
            conn.commit()
            logging.info(f"Session logged: {app_name}, Interaction: {self.session.interaction_rate}")
        except Exception as e:
            logging.error(f"Failed to log session: {e}")
        finally:
            conn.close()
            self.session.reset_events()

    def log_multi_modal(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ocr_data_to_store = {str(k): {"score": float(v.get("score", 0.5)), "count": int(v.get("count", 1))} 
                                 if isinstance(v, dict) else {"score": float(v), "count": 1} 
                                 for k, v in (self.session.ocr_keywords or {}).items()}
            c.execute(
                """INSERT INTO multi_modal_logs
                (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, 
                intent_label, intent_confidence, memory_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (timestamp, self.session.window_title, json.dumps(ocr_data_to_store), self.session.audio_label,
                 int(self.session.attention_score), int(self.session.interaction_rate), self.session.intent_label,
                 float(self.session.intent_confidence), float(max([float(self.G.nodes[kw].get('memory_score', 0.0)) 
                                                                  for kw in self.session.ocr_keywords.keys()] or [0.0])))
            )
            conn.commit()
        except Exception as e:
            logging.error(f"Multi-modal log failed: {e}")
        finally:
            conn.close()

    # -----------------------------
    # Notifications
    # -----------------------------
    def maybe_notify(self, concept: str, memory_score: float):
        now = datetime.now()
        last_reminded_str = self.G.nodes[concept].get('last_reminded_time')
        try:
            last_reminded = datetime.fromisoformat(last_reminded_str) if last_reminded_str else now - self.REMINDER_COOLDOWN
        except Exception:
            last_reminded = now - self.REMINDER_COOLDOWN

        if memory_score < self.MEMORY_THRESHOLD and (now - last_reminded >= self.REMINDER_COOLDOWN):
            notification.notify(
                title="Time to Review!",
                message=f"Concept: {concept}\nMemory Score: {memory_score:.2f}",
                timeout=5
            )
            self.G.nodes[concept]['last_reminded_time'] = now.isoformat()
            self.G.nodes[concept]['next_review_time'] = (now + timedelta(hours=1)).isoformat()

    # -----------------------------
    # Tracker loop
    # -----------------------------
    def run(self, stop_event: Event = None):
        if stop_event is None:
            stop_event = Event()
        self.start_listeners()
        SAVE_INTERVAL = 300

        while not stop_event.is_set():
            try:
                window, interaction = self.get_active_window()
                self.log_session()

                # ---- Audio ----
                self.counters["audio"] += TRACK_INTERVAL
                if self.counters["audio"] >= AUDIO_INTERVAL:
                    self.session.audio_label, self.session.audio_confidence = self.classify_audio()
                    self.counters["audio"] = 0

                # ---- OCR ----
                self.counters["ocr"] += TRACK_INTERVAL
                if self.counters["ocr"] >= SCREENSHOT_INTERVAL:
                    self.session.ocr_keywords = self.capture_ocr()
                    self.counters["ocr"] = 0

                # ---- Webcam ----
                self.counters["webcam"] += TRACK_INTERVAL
                if self.counters["webcam"] >= WEBCAM_INTERVAL and self.user_allow_webcam:
                    self.session.attention_score = self.capture_attention()
                    self.counters["webcam"] = 0

                # ---- Intent ----
                self.session.intent_label, self.session.intent_confidence = self.predict_intent()

                # ---- Memory & KG ----
                self.update_memory()

                # ---- Log multi-modal ----
                self.log_multi_modal()

                # ---- Save KG ----
                self.counters["save"] += TRACK_INTERVAL
                if self.counters["save"] >= SAVE_INTERVAL:
                    self.save_kg()
                    self.counters["save"] = 0

                time.sleep(TRACK_INTERVAL)

            except KeyboardInterrupt:
                logging.info("Tracker stopped by user.")
                break
            except Exception as e:
                logging.error(f"Unexpected error in loop: {e}")
                time.sleep(TRACK_INTERVAL)

        self.save_kg()
        self.kb_listener.stop()
        self.ms_listener.stop()

    # -----------------------------
    # Helper methods (audio, OCR, webcam, intent, memory)
    # -----------------------------
    def classify_audio(self):
        try:
            audio = record_audio()
            if audio_clf:
                features = audio_extract_features(audio).reshape(1, -1)
                label = audio_clf.predict(features)[0]
                confidence = float(max(audio_clf.predict_proba(features)[0]))
                return label, confidence
        except Exception as e:
            logging.error(f"Audio classification error: {e}")
        return "unknown", 0.0

    def capture_ocr(self):
        try:
            ocr_data = ocr_pipeline() or {}
            keywords = ocr_data.get("keywords", {}) or {}
            keywords = {str(k): {"score": float(v.get("score", 0.5)) if isinstance(v, dict) else float(v),
                                 "count": int(v.get("count", 1)) if isinstance(v, dict) else 1}
                        for k, v in keywords.items()}
            if keywords:
                add_concepts(list(keywords.keys()))
            return keywords
        except Exception as e:
            logging.error(f"OCR capture error: {e}")
        return {}

    def capture_attention(self):
        try:
            frame = webcam_pipeline()
            faces, num_faces = self.face_detector.detect_faces(frame)
            logging.info(f"Faces detected: {num_faces}")
            return int(num_faces)
        except Exception as e:
            logging.error(f"Webcam attention error: {e}")
        return 0

    def predict_intent(self):
        data = predict_intent_live(self.session.ocr_keywords, self.session.audio_label,
                                   self.session.attention_score, self.session.interaction_rate,
                                   use_webcam=self.user_allow_webcam)
        return data.get("intent_label", "unknown"), float(data.get("confidence", 0.0))

    def update_memory(self):
        for concept, info in self.session.ocr_keywords.items():
            try:
                if concept not in self.G.nodes:
                    add_concepts([concept])
                last_review = self.G.nodes[concept].get("last_review") or datetime.now().isoformat()
                last_review_dt = datetime.fromisoformat(last_review) if isinstance(last_review, str) else last_review
                mem_score = compute_memory_score(last_review_dt, 0.1, float(self.G.nodes[concept].get("intent_conf", 1.0)),
                                                self.session.attention_score, 1.0)
                mem_score *= min(1.0, float(info.get("score", 0.5)) + 0.5)
                mem_score *= min(1.5, 1 + 0.05 * (int(info.get("count", 1)) - 1))
                next_review = schedule_next_review(last_review_dt, mem_score, 0.1)

                self.G.nodes[concept]["memory_score"] = mem_score
                self.G.nodes[concept]["next_review_time"] = next_review.isoformat() if isinstance(next_review, datetime) else str(next_review)
                self.G.nodes[concept]["last_review"] = datetime.now().isoformat()
                self.maybe_notify(concept, mem_score)
            except Exception as e:
                logging.error(f"Memory update failed for {concept}: {e}")

    def save_kg(self):
        os.makedirs("data", exist_ok=True)
        with open("data/knowledge_graph.pkl", "wb") as f:
            pickle.dump(self.G, f)
        logging.info("Knowledge graph saved.")

# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    USER_ALLOW_WEBCAM = input("Enable webcam attention? (y/n): ").lower() == "y"
    tracker = Tracker(USER_ALLOW_WEBCAM)
    tracker.run()
