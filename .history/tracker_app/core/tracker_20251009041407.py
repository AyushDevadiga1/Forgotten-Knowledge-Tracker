# ==========================================================
# core/tracker.py
# ==========================================================
"""
Main tracker loop: listens for user interactions, captures audio/ocr/webcam,
predicts intent, updates knowledge graph & memory model, and logs multi-modal
events to the database.

Keep this file runnable as a script for local testing.
"""

import json
import os
import pickle
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from threading import Event
from typing import Dict, Any, Tuple, Optional

from pynput import keyboard, mouse
import win32gui
from plyer import notification

from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db
from config import (
    DB_PATH,
    TRACK_INTERVAL,
    SCREENSHOT_INTERVAL,
    AUDIO_INTERVAL,
    WEBCAM_INTERVAL,
    USER_ALLOW_WEBCAM,
)
from core.ocr_module import ocr_pipeline
from core.audio_module import record_audio, extract_features as audio_extract_features
from core.webcam_module import webcam_pipeline
from core.intent_module import extract_features as intent_extract_features
from core.knowledge_graph import add_concepts, get_graph, add_edges
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve
from core.face_detection_module import FaceDetector

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    filename="logs/tracker.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# -----------------------------
# Load optional classifiers
# -----------------------------
audio_clf = None
audio_clf_path = "core/audio_classifier.pkl"
if os.path.exists(audio_clf_path):
    try:
        with open(audio_clf_path, "rb") as f:
            audio_clf = pickle.load(f)
        logging.info("Audio classifier loaded.")
    except Exception as e:
        logging.exception("Failed to load audio classifier: %s", e)

intent_clf = None
intent_label_map = None
intent_clf_path = "core/intent_classifier.pkl"
intent_map_path = "core/intent_label_map.pkl"
if os.path.exists(intent_clf_path) and os.path.exists(intent_map_path):
    try:
        with open(intent_clf_path, "rb") as f:
            intent_clf = pickle.load(f)
        with open(intent_map_path, "rb") as f:
            intent_label_map = pickle.load(f)
        logging.info("Intent classifier & label map loaded.")
    except Exception as e:
        logging.exception("Failed to load intent classifier/label map: %s", e)

# -----------------------------
# User consent helper
# -----------------------------
def ask_user_permissions() -> None:
    """Ask user whether to allow webcam attention tracking (updates USER_ALLOW_WEBCAM)."""
    global USER_ALLOW_WEBCAM
    try:
        choice = input("Do you want to enable webcam attention tracking? (y/n): ").strip().lower()
        USER_ALLOW_WEBCAM = choice == "y"
        logging.info("User webcam consent: %s", USER_ALLOW_WEBCAM)
    except Exception:
        logging.warning("Unable to read user consent input; defaulting to False.")
        USER_ALLOW_WEBCAM = False

# -----------------------------
# Interaction counters (thread-safe enough for this use)
# -----------------------------
class InteractionCounter:
    def __init__(self):
        self.keyboard = 0
        self.mouse = 0

    def total(self) -> int:
        return int(self.keyboard + self.mouse)

    def reset(self) -> None:
        self.keyboard = 0
        self.mouse = 0

counters = InteractionCounter()

# -----------------------------
# Listener callbacks
# -----------------------------
def _on_key_press(_key) -> None:
    counters.keyboard += 1

def _on_mouse_click(_x, _y, _button, pressed) -> None:
    if pressed:
        counters.mouse += 1

def start_listeners() -> Tuple[keyboard.Listener, mouse.Listener]:
    kb = keyboard.Listener(on_press=_on_key_press)
    ms = mouse.Listener(on_click=_on_mouse_click)
    kb.start()
    ms.start()
    return kb, ms

# -----------------------------
# Active window retrieval
# -----------------------------
def get_active_window() -> Tuple[str, int]:
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or "Unknown"
    except Exception:
        title = "Unknown"
    return title, counters.total()

# -----------------------------
# DB logging helpers
# -----------------------------
def log_session(window_title: str, interaction_rate: int) -> None:
    """Insert a session row (start_ts == end_ts for point events)."""
    counters.reset()
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        app_name = window_title.split(" - ")[-1] if " - " in window_title else window_title
        c.execute(
            """
            INSERT INTO sessions (start_ts, end_ts, app_name, window_title, interaction_rate)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ts, ts, app_name, window_title, int(interaction_rate)),
        )
        conn.commit()
        logging.debug("Logged session: %s (%s)", app_name, interaction_rate)
    except Exception as e:
        logging.exception("Failed to log session: %s", e)
    finally:
        conn.close()

def log_multi_modal(
    window: str,
    ocr_keywords: Dict[str, Any],
    audio_label: str,
    attention_score: int,
    interaction_rate: int,
    intent_label: str,
    intent_confidence: float,
    memory_score: float = 0.0,
) -> None:
    """Insert a multi-modal event row. OCR saved as JSON string."""
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_ocr = {}
        if ocr_keywords:
            for kw, info in ocr_keywords.items():
                if isinstance(info, dict):
                    safe_ocr[str(kw)] = {
                        "score": float(info.get("score", 0.5)),
                        "count": int(info.get("count", 1)),
                    }
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
                int(attention_score),
                int(interaction_rate),
                intent_label,
                float(intent_confidence),
                float(memory_score),
            ),
        )
        conn.commit()
        logging.debug("Logged multi-modal event for '%s' intent='%s'", window, intent_label)
    except Exception as e:
        logging.exception("Failed to write multi_modal_logs: %s", e)
    finally:
        conn.close()

# -----------------------------
# Knowledge graph save helper
# -----------------------------
def save_knowledge_graph() -> None:
    try:
        G = get_graph()
        os.makedirs("data", exist_ok=True)
        with open("data/knowledge_graph.pkl", "wb") as f:
            pickle.dump(G, f)
        logging.info("Knowledge graph saved.")
    except Exception as e:
        logging.exception("Failed to save knowledge graph: %s", e)

# -----------------------------
# Audio / Intent helpers
# -----------------------------
def classify_audio_live() -> Tuple[str, float]:
    audio = record_audio()
    if audio_clf is not None:
        try:
            feats = audio_extract_features(audio).reshape(1, -1)
            label = audio_clf.predict(feats)[0]
            confidence = float(max(audio_clf.predict_proba(feats)[0]))
            return label, confidence
        except Exception:
            logging.exception("Audio classification failed; falling back to unknown.")
            return "unknown", 0.0
    return "unknown", 0.0

def predict_intent_live(
    ocr_keywords: Dict[str, Any], audio_label: str, attention_score: int, interaction_rate: int, use_webcam: bool = False
) -> Dict[str, Any]:
    """Predict intent using model or fallback rules; returns dict with label & confidence."""
    try:
        att = int(attention_score or 0)
        ir = int(interaction_rate or 0)
        features = intent_extract_features(ocr_keywords, audio_label, att, ir, use_webcam=use_webcam)
        if intent_clf is not None and intent_label_map is not None:
            pred_idx = intent_clf.predict(features)[0]
            confidence = float(max(intent_clf.predict_proba(features)[0]))
            try:
                label = intent_label_map.inverse_transform([int(pred_idx)])[0]
            except Exception:
                try:
                    label = intent_label_map[int(pred_idx)]
                except Exception:
                    label = str(pred_idx)
            return {"intent_label": label, "confidence": confidence}
        # fallback:
        if audio_label == "speech" and ir > 5:
            if use_webcam and att > 50:
                return {"intent_label": "studying", "confidence": 0.8}
            return {"intent_label": "passive", "confidence": 0.6}
        if ir < 2:
            return {"intent_label": "idle", "confidence": 0.7}
        return {"intent_label": "passive", "confidence": 0.6}
    except Exception as e:
        logging.exception("Intent prediction failed: %s", e)
        return {"intent_label": "unknown", "confidence": 0.0}

# -----------------------------
# Memory/reminder helpers (webcam-safe)
# -----------------------------
MEMORY_THRESHOLD = 0.6
REMINDER_COOLDOWN = timedelta(minutes=30)

def maybe_notify(concept: str, memory_score: float, graph, use_attention: bool = True) -> None:
    """
    Notify user if memory_score < threshold, respecting REMINDER_COOLDOWN.
    If use_attention=False, skips attention-related scaling.
    """
    now = datetime.now()
    last_reminded_str = graph.nodes[concept].get("last_reminded_time")
    
    try:
        last_reminded = datetime.fromisoformat(last_reminded_str) if last_reminded_str else now - REMINDER_COOLDOWN
    except Exception:
        last_reminded = now - REMINDER_COOLDOWN

    # Only notify if cooldown passed
    if memory_score < MEMORY_THRESHOLD and (now - last_reminded >= REMINDER_COOLDOWN):
        try:
            notification.notify(
                title="Time to Review!",
                message=f"Concept: {concept}\nMemory Score: {memory_score:.2f}",
                timeout=5,
            )
            graph.nodes[concept]["last_reminded_time"] = now.isoformat()
            graph.nodes[concept]["next_review_time"] = (now + timedelta(hours=1)).isoformat()
            logging.info("Reminder sent for concept '%s' (score: %.3f)", concept, memory_score)
        except Exception:
            logging.exception("Failed to send notification for concept '%s'", concept)
    else:
        if not use_attention:
            logging.debug(
                "Webcam off or attention ignored; skipping reminder for '%s'.", concept
            )


# -----------------------------
# Tracker loop
# -----------------------------
def track_loop(stop_event: Optional[Event] = None) -> None:
    if stop_event is None:
        stop_event = Event()

    # ensure DB tables exist
    init_db()
    init_multi_modal_db()
    init_memory_decay_db()

    kb_listener, ms_listener = start_listeners()
    face_detector = FaceDetector()
    SAVE_INTERVAL = 300  # seconds
    ocr_counter = audio_counter = webcam_counter = save_counter = 0

    latest_ocr: Dict[str, Any] = {}
    latest_audio = "silence"
    latest_attention = 0
    latest_interaction = 0

    G = get_graph()

    try:
        logging.info("Tracker started.")
        print("Starting tracker...")
        while not stop_event.is_set():
            try:
                # Active window and interactions
                window, latest_interaction = get_active_window()
                log_session(window, latest_interaction)

                # -------- Audio --------
                audio_counter += TRACK_INTERVAL
                if audio_counter >= AUDIO_INTERVAL:
                    latest_audio, audio_conf = classify_audio_live()
                    audio_counter = 0

                # -------- OCR --------
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
                        latest_ocr = normalized
                        if latest_ocr:
                            add_concepts(list(latest_ocr.keys()))
                    except Exception:
                        latest_ocr = {}
                    ocr_counter = 0
                    G = get_graph()

                # -------- Memory & Reminders --------
                mem_scores = {}
                for concept, info in latest_ocr.items():
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
                        attention_score = int(latest_attention or 0)
                        audio_conf = 1.0
                        kw_score = float(info.get("score", 0.5))
                        count = int(info.get("count", 1))

                        mem_score = compute_memory_score(last_review, lambda_val, intent_conf, attention_score, audio_conf)
                        mem_score = float(mem_score) * min(1.0, kw_score + 0.5)
                        mem_score = mem_score * min(1.5, 1 + 0.05 * (count - 1))

                        next_review = schedule_next_review(last_review, mem_score, lambda_val)

                        G.nodes[concept]["memory_score"] = float(mem_score)
                        G.nodes[concept]["next_review_time"] = next_review.isoformat() if hasattr(next_review, "isoformat") else str(next_review)
                        G.nodes[concept]["last_review"] = datetime.now().isoformat()
                        G.nodes[concept]["intent_conf"] = float(intent_conf)

                        maybe_notify(concept, mem_score, G)
                        log_forgetting_curve(concept, last_review, observed_usage=count)

                        mem_scores[concept] = mem_score
                    except Exception:
                        continue

                # -------- Webcam --------
                webcam_counter += TRACK_INTERVAL
                if webcam_counter >= WEBCAM_INTERVAL and USER_ALLOW_WEBCAM:
                    try:
                        frame = webcam_pipeline()
                        faces, num_faces = face_detector.detect_faces(frame)
                        latest_attention = int(num_faces)
                    except Exception:
                        latest_attention = 0
                    webcam_counter = 0

                # -------- Intent --------
                intent_data = predict_intent_live(
                    latest_ocr, latest_audio, latest_attention, latest_interaction, use_webcam=USER_ALLOW_WEBCAM
                )

                # Add co-occurrence edges (safe)
                try:
                    add_edges(latest_ocr, latest_audio, intent_data.get("intent_label", "unknown"))
                except Exception:
                    pass

                # -------- Multi-modal logging --------
                try:
                    memory_score = max(mem_scores.values() or [0.0])
                    log_multi_modal(
                        window,
                        latest_ocr,
                        latest_audio,
                        latest_attention,
                        latest_interaction,
                        intent_data.get("intent_label", "unknown"),
                        float(intent_data.get("confidence", 0.0)),
                        memory_score=memory_score,
                    )
                except Exception:
                    pass

                # -------- Periodic Knowledge Graph Save --------
                save_counter += TRACK_INTERVAL
                if save_counter >= SAVE_INTERVAL:
                    save_knowledge_graph()
                    save_counter = 0

                # -------- Session Summary Print --------
                print(f"\n[Session Summary]")
                print(f"Window: {window}")
                print(f"Intent: {intent_data.get('intent_label')} | Confidence: {intent_data.get('confidence', 0.0):.2f}")
                print(f"Audio: {latest_audio}")
                print(f"Attention: {latest_attention}")
                print(f"OCR Keywords: {list(latest_ocr.keys())[:5]}{'...' if len(latest_ocr) > 5 else ''}")
                print(f"Memory Score (max concept): {memory_score:.3f}")
                print("-" * 40)

                time.sleep(TRACK_INTERVAL)

            except KeyboardInterrupt:
                print("Tracker stopped by user.")
                logging.info("Tracker stopped by KeyboardInterrupt.")
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
        logging.info("Tracker terminated cleanly.")

# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    ask_user_permissions()
    logging.info("Starting tracker (main).")
    print("Starting tracker...")
    track_loop()
