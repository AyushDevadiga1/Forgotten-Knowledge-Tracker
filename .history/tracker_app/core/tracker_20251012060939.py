# ==========================================================
# core/tracker.py
# ==========================================================
"""
Tracker v2 (IEEE-Ready)
-----------------------
- Captures real-time multi-modal data: audio, OCR, webcam
- Tracks user interactions (keyboard/mouse)
- Computes intent and memory score per concept
- Updates knowledge graph & co-occurrence edges
- Triggers spaced-review reminders
- Logs events to multi-modal DB and session table
- Safe failover and centralized logging
"""

import os
import json
import pickle
import time
import sqlite3
import logging
from datetime import datetime, timedelta
from threading import Event
from typing import Dict, Any, Optional, Tuple

from pynput import keyboard, mouse
import win32gui
from plyer import notification

from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db, log_multi_modal_event
from core.ocr_module import ocr_pipeline
from core.audio_module import record_audio, extract_features as audio_extract_features
from core.webcam_module import webcam_pipeline
from core.intent_module import extract_features as intent_extract_features
from core.knowledge_graph import add_concepts, get_graph, add_edges
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve
from core.face_detection_module import FaceDetector
from config import DB_PATH, TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL, USER_ALLOW_WEBCAM

# -----------------------------
# Logger setup
# -----------------------------
if not os.path.exists("logs"):
    os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/tracker.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------------
# Load classifiers
# -----------------------------
audio_clf, intent_clf, intent_label_map = None, None, None

try:
    with open("core/audio_classifier.pkl", "rb") as f:
        audio_clf = pickle.load(f)
    logger.info("Audio classifier loaded.")
except Exception:
    logger.warning("No audio classifier found.")

try:
    with open("core/intent_classifier.pkl", "rb") as f:
        intent_clf = pickle.load(f)
    with open("core/intent_label_map.pkl", "rb") as f:
        intent_label_map = pickle.load(f)
    logger.info("Intent classifier & label map loaded.")
except Exception:
    logger.warning("No intent classifier/label map found.")

# -----------------------------
# User consent
# -----------------------------
def ask_user_permissions() -> None:
    global USER_ALLOW_WEBCAM
    try:
        choice = input("Enable webcam attention tracking? (y/n): ").strip().lower()
        USER_ALLOW_WEBCAM = choice == "y"
        logger.info("User webcam consent: %s", USER_ALLOW_WEBCAM)
    except Exception:
        USER_ALLOW_WEBCAM = False
        logger.warning("Defaulting webcam consent to False.")

# -----------------------------
# Interaction counters
# -----------------------------
class InteractionCounter:
    def __init__(self):
        self.keyboard = 0
        self.mouse = 0

    def total(self) -> int:
        return int(self.keyboard + self.mouse)

    def reset(self):
        self.keyboard = 0
        self.mouse = 0

counters = InteractionCounter()

def _on_key_press(_key):
    counters.keyboard += 1

def _on_mouse_click(_x, _y, _button, pressed):
    if pressed:
        counters.mouse += 1

def start_listeners() -> Tuple[keyboard.Listener, mouse.Listener]:
    kb = keyboard.Listener(on_press=_on_key_press)
    ms = mouse.Listener(on_click=_on_mouse_click)
    kb.start()
    ms.start()
    return kb, ms

# -----------------------------
# Active window
# -----------------------------
def get_active_window() -> Tuple[str, int]:
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or "Unknown"
    except Exception:
        title = "Unknown"
    return title, counters.total()

# -----------------------------
# Logging helpers
# -----------------------------
def log_session(window_title: str, interaction_rate: int):
    counters.reset()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        app_name = window_title.split(" - ")[-1] if " - " in window_title else window_title
        c.execute(
            "INSERT INTO sessions (start_ts, end_ts, app_name, window_title, interaction_rate) VALUES (?, ?, ?, ?, ?)",
            (ts, ts, app_name, window_title, int(interaction_rate)),
        )
        conn.commit()
    except Exception:
        logger.exception("Failed to log session")
    finally:
        conn.close()

def log_multi_modal(window: str, ocr_keywords: Dict[str, Any], audio_label: str, attention_score: Optional[int],
                    interaction_rate: int, intent_label: str, intent_confidence: float, memory_score: float = 0.0):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_ocr = {}
        if ocr_keywords:
            for kw, info in ocr_keywords.items():
                if isinstance(info, dict):
                    safe_ocr[str(kw)] = {"score": float(info.get("score", 0.5)), "count": int(info.get("count", 1))}
                else:
                    safe_ocr[str(kw)] = {"score": float(info), "count": 1}
        c.execute(
            """
            INSERT INTO multi_modal_logs
            (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                window,
                json.dumps(safe_ocr),
                audio_label,
                int(attention_score) if attention_score is not None else 0,
                int(interaction_rate),
                intent_label,
                float(intent_confidence),
                float(memory_score),
            ),
        )
        conn.commit()
    except Exception:
        logger.exception("Failed to write multi_modal_logs")
    finally:
        conn.close()

# -----------------------------
# Knowledge graph
# -----------------------------
def save_knowledge_graph():
    try:
        G = get_graph()
        os.makedirs("data", exist_ok=True)
        with open("data/knowledge_graph.pkl", "wb") as f:
            pickle.dump(G, f)
        logger.info("Knowledge graph saved.")
    except Exception:
        logger.exception("Failed to save knowledge graph")

# -----------------------------
# Audio & intent
# -----------------------------
def classify_audio_live() -> Tuple[str, float]:
    try:
        audio = record_audio()
        if audio_clf:
            feats = audio_extract_features(audio).reshape(1, -1)
            label = audio_clf.predict(feats)[0]
            confidence = float(max(audio_clf.predict_proba(feats)[0]))
            return label, confidence
    except Exception:
        logger.exception("Audio classification failed")
    return "unknown", 0.0

def predict_intent_live(ocr_keywords: Dict[str, Any], audio_label: str, attention_score: Optional[int],
                        interaction_rate: int, use_webcam: bool = False) -> Dict[str, Any]:
    try:
        att = int(attention_score or 0)
        ir = int(interaction_rate or 0)
        features = intent_extract_features(ocr_keywords, audio_label, att, ir, use_webcam=use_webcam)
        if intent_clf and intent_label_map:
            pred_idx = intent_clf.predict(features)[0]
            confidence = float(max(intent_clf.predict_proba(features)[0]))
            try:
                label = intent_label_map.inverse_transform([int(pred_idx)])[0]
            except Exception:
                label = str(pred_idx)
            return {"intent_label": label, "confidence": confidence}
        # Fallback heuristics
        if audio_label == "speech" and ir > 5:
            if use_webcam and att > 50:
                return {"intent_label": "studying", "confidence": 0.8}
            return {"intent_label": "passive", "confidence": 0.6}
        if ir < 2:
            return {"intent_label": "idle", "confidence": 0.7}
        return {"intent_label": "passive", "confidence": 0.6}
    except Exception:
        logger.exception("Intent prediction failed")
        return {"intent_label": "unknown", "confidence": 0.0}

# -----------------------------
# Memory & reminders
# -----------------------------
MEMORY_THRESHOLD = 0.6
REMINDER_COOLDOWN = timedelta(minutes=30)

def maybe_notify(concept: str, memory_score: float, graph, use_attention: bool = True):
    now = datetime.now()
    last_reminded_str = graph.nodes[concept].get("last_reminded_time")
    try:
        last_reminded = datetime.fromisoformat(last_reminded_str) if last_reminded_str else now - REMINDER_COOLDOWN
    except Exception:
        last_reminded = now - REMINDER_COOLDOWN
    if memory_score < MEMORY_THRESHOLD and (now - last_reminded >= REMINDER_COOLDOWN):
        try:
            notification.notify(
                title="Time to Review!",
                message=f"Concept: {concept}\nMemory Score: {memory_score:.2f}",
                timeout=5,
            )
            graph.nodes[concept]["last_reminded_time"] = now.isoformat()
            graph.nodes[concept]["next_review_time"] = (now + timedelta(hours=1)).isoformat()
            logger.info("Reminder sent for concept '%s' (score: %.3f)", concept, memory_score)
        except Exception:
            logger.exception("Failed to send notification for concept '%s'", concept)

# -----------------------------
# Tracker loop
# -----------------------------
_latest_ocr: Dict[str, Any] = {}
_latest_attention: Optional[int] = 0

def track_loop(stop_event: Optional[Event] = None):
    global _latest_ocr, _latest_attention
    if stop_event is None:
        stop_event = Event()

    init_db()
    init_multi_modal_db()
    init_memory_decay_db()

    kb_listener, ms_listener = start_listeners()
    face_detector = FaceDetector()

    SAVE_INTERVAL = 300  # seconds
    ocr_counter = audio_counter = webcam_counter = save_counter = 0
    latest_audio = "silence"
    latest_interaction = 0
    G = get_graph()

    try:
        logger.info("Tracker started.")
        print("Starting tracker...")
        while not stop_event.is_set():
            try:
                # --- Active window + interaction ---
                window, latest_interaction = get_active_window()
                log_session(window, latest_interaction)

                # --- Audio ---
                audio_counter += TRACK_INTERVAL
                if audio_counter >= AUDIO_INTERVAL:
                    latest_audio, audio_conf = classify_audio_live()
                    audio_counter = 0

                # --- OCR ---
                ocr_counter += TRACK_INTERVAL
                if ocr_counter >= SCREENSHOT_INTERVAL:
                    try:
                        ocr_data = ocr_pipeline() or {}
                        raw_keywords = ocr_data.get("keywords", {}) or {}
                        normalized = {}
                        for kw, info in raw_keywords.items():
                            if isinstance(info, dict):
                                normalized[str(kw)] = {"score": float(info.get("score", 0.5)), "count": int(info.get("count", 1))}
                            else:
                                normalized[str(kw)] = {"score": float(info), "count": 1}
                        _latest_ocr = normalized
                        if _latest_ocr:
                            add_concepts(list(_latest_ocr.keys()))
                    except Exception:
                        _latest_ocr = {}
                    ocr_counter = 0
                    G = get_graph()

                # --- Webcam ---
                webcam_counter += TRACK_INTERVAL
                if webcam_counter >= WEBCAM_INTERVAL:
                    if USER_ALLOW_WEBCAM:
                        try:
                            frame = webcam_pipeline()
                            faces, num_faces = face_detector.detect_faces(frame)
                            _latest_attention = int(num_faces)
                        except Exception:
                            _latest_attention = None
                            logger.exception("Webcam failed")
                    else:
                        _latest_attention = None
                    webcam_counter = 0

                # --- Memory & reminders ---
                mem_scores = {}
                for concept, info in _latest_ocr.items():
                    try:
                        if concept not in G.nodes:
                            add_concepts([concept])
                            G = get_graph()

                        last_review = G.nodes[concept].get("last_review")
                        if isinstance(last_review, str):
                            try:
                                last_review = datetime.fromisoformat(last_review)
                            except Exception:
                                last_review = datetime.now()
                        elif last_review is None:
                            last_review = datetime.now()

                        lambda_val = 0.1
                        intent_conf = float(G.nodes[concept].get("intent_conf", 1.0))
                        audio_conf = 1.0
                        kw_score = float(info.get("score", 0.5))
                        count = int(info.get("count", 1))
                        att_score = int(_latest_attention) if _latest_attention is not None else None

                        mem_score = compute_memory_score(last_review, lambda_val, intent_conf, att_score, audio_conf)
                        mem_score *= min(1.0, kw_score + 0.5)
                        mem_score *= min(1.5, 1 + 0.05 * (count - 1))

                        next_review = schedule_next_review(last_review, mem_score, lambda_val)

                        G.nodes[concept]["memory_score"] = float(mem_score)
                        G.nodes[concept]["next_review_time"] = next_review.isoformat() if hasattr(next_review, "isoformat") else str(next_review)
                        G.nodes[concept]["last_review"] = datetime.now().isoformat()
                        G.nodes[concept]["intent_conf"] = float(intent_conf)

                        maybe_notify(concept, mem_score, G, use_attention=(att_score is not None))
                        log_forgetting_curve(concept, last_review, observed_usage=count)
                        mem_scores[concept] = mem_score
                    except Exception:
                        logger.exception("Memory update failed for '%s'", concept)

                # --- Intent ---
                intent_data = predict_intent_live(_latest_ocr, latest_audio, _latest_attention, latest_interaction, use_webcam=USER_ALLOW_WEBCAM)

                # --- Knowledge graph edges ---
                try:
                    add_edges(_latest_ocr, latest_audio, intent_data.get("intent_label", "unknown"))
                except Exception:
                    pass

                # --- Multi-modal log ---
                try:
                    memory_score = max(mem_scores.values() or [0.0])
                    log_multi_modal(window, _latest_ocr, latest_audio, _latest_attention, latest_interaction, intent_data.get("intent_label", "unknown"), float(intent_data.get("confidence", 0.0)), memory_score)
                except Exception:
                    pass

                # --- Periodic save ---
                save_counter += TRACK_INTERVAL
                if save_counter >= SAVE_INTERVAL:
                    save_knowledge_graph()
                    save_counter = 0

                # --- Console summary ---
                print(f"\n[Session Summary]")
                print(f"Window: {window}")
                print(f"Intent: {intent_data.get('intent_label')} | Confidence: {intent_data.get('confidence', 0.0):.2f}")
                print(f"Audio: {latest_audio}")
                print(f"Attention: {_latest_attention}")
                print(f"OCR Keywords: {list(_latest_ocr.keys())[:5]}{'...' if len(_latest_ocr) > 5 else ''}")
                print(f"Memory Score (max): {memory_score:.3f}")
                print("-" * 50)

                time.sleep(TRACK_INTERVAL)
            except KeyboardInterrupt:
                logger.info("Tracker stopped by user.")
                break
            except Exception:
                time.sleep(TRACK_INTERVAL)
                continue
    finally:
        try:
            save_knowledge_graph()
        except Exception:
            pass
        try:
            kb_listener.stop()
            ms_listener.stop()
        except Exception:
            pass
        logger.info("Tracker terminated cleanly.")

# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    ask_user_permissions()
    track_loop()
