# ==========================================================
# core/tracker.py
# ==========================================================

import os
import json
import pickle
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from threading import Event, Thread
from typing import Dict, Any, Optional, Tuple

from pynput import keyboard, mouse
import win32gui
from plyer import notification

from config import (
    DB_PATH, TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL, USER_ALLOW_WEBCAM
)
from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db
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
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/tracker.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# -----------------------------
# Safe decorator
# -----------------------------
def safe(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception(f"Exception in {func.__name__}")
            return None
    return wrapper

# -----------------------------
# Tracker Class
# -----------------------------
class Tracker:
    def __init__(self):
        self.db_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.db_cursor = self.db_conn.cursor()
        self.counters = {"keyboard": 0, "mouse": 0}
        self.latest_ocr: Dict[str, Any] = {}
        self.latest_attention: Optional[int] = 0
        self.latest_audio = "silence"
        self.latest_interaction = 0
        self.face_detector = FaceDetector()
        self.graph = get_graph()
        self.stop_event = Event()

        # Load models
        self.audio_clf, self.intent_clf, self.intent_label_map = self.load_models()

    @safe
    def load_models(self):
        audio_clf = intent_clf = intent_label_map = None
        if os.path.exists("core/audio_classifier.pkl"):
            with open("core/audio_classifier.pkl", "rb") as f:
                audio_clf = pickle.load(f)
        if os.path.exists("core/intent_classifier.pkl") and os.path.exists("core/intent_label_map.pkl"):
            with open("core/intent_classifier.pkl", "rb") as f:
                intent_clf = pickle.load(f)
            with open("core/intent_label_map.pkl", "rb") as f:
                intent_label_map = pickle.load(f)
        return audio_clf, intent_clf, intent_label_map

    # -----------------------------
    # Listeners
    # -----------------------------
    def _on_key_press(self, _key): self.counters["keyboard"] += 1
    def _on_mouse_click(self, _x, _y, _button, pressed): 
        if pressed: self.counters["mouse"] += 1

    @safe
    def start_listeners(self):
        kb = keyboard.Listener(on_press=self._on_key_press)
        ms = mouse.Listener(on_click=self._on_mouse_click)
        kb.start()
        ms.start()
        return kb, ms

    # -----------------------------
    # Active window
    # -----------------------------
    @safe
    def get_active_window(self) -> Tuple[str, int]:
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd) or "Unknown"
        except Exception:
            title = "Unknown"
        return title, self.counters["keyboard"] + self.counters["mouse"]

    # -----------------------------
    # DB logging
    # -----------------------------
    @safe
    def log_session(self, window_title: str, interaction_rate: int):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        app_name = window_title.split(" - ")[-1] if " - " in window_title else window_title
        self.db_cursor.execute(
            "INSERT INTO sessions (start_ts, end_ts, app_name, window_title, interaction_rate) VALUES (?, ?, ?, ?, ?)",
            (ts, ts, app_name, window_title, int(interaction_rate)),
        )
        self.db_conn.commit()
        self.counters["keyboard"] = self.counters["mouse"] = 0

    @safe
    def log_multi_modal(self, window, ocr, audio_label, attention, interaction, intent_label, intent_conf, memory_score=0.0):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_ocr = {str(k): {"score": float(v.get("score", 0.5)), "count": int(v.get("count",1))} for k,v in ocr.items()} if ocr else {}
        self.db_cursor.execute(
            """
            INSERT INTO multi_modal_logs
            (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, window, json.dumps(safe_ocr), audio_label, int(attention or 0), int(interaction),
             intent_label, float(intent_conf), float(memory_score))
        )
        self.db_conn.commit()

    # -----------------------------
    # Audio / Intent
    # -----------------------------
    @safe
    def classify_audio_live(self):
        audio = record_audio()
        if self.audio_clf:
            feats = audio_extract_features(audio).reshape(1, -1)
            label = self.audio_clf.predict(feats)[0]
            confidence = float(max(self.audio_clf.predict_proba(feats)[0]))
            return label, confidence
        return "unknown", 0.0

    @safe
    def predict_intent_live(self, ocr_keywords, audio_label, attention_score, interaction_rate):
        att = int(attention_score or 0)
        ir = int(interaction_rate or 0)
        features = intent_extract_features(ocr_keywords, audio_label, att, ir, use_webcam=USER_ALLOW_WEBCAM)
        if self.intent_clf and self.intent_label_map:
            pred_idx = self.intent_clf.predict(features)[0]
            confidence = float(max(self.intent_clf.predict_proba(features)[0]))
            try:
                label = self.intent_label_map.inverse_transform([int(pred_idx)])[0]
            except Exception:
                label = str(pred_idx)
            return {"intent_label": label, "confidence": confidence}
        # fallback heuristics
        if audio_label == "speech" and ir > 5:
            if USER_ALLOW_WEBCAM and att > 50: return {"intent_label": "studying", "confidence": 0.8}
            return {"intent_label": "passive", "confidence": 0.6}
        if ir < 2: return {"intent_label": "idle", "confidence": 0.7}
        return {"intent_label": "passive", "confidence": 0.6}

    # -----------------------------
    # Tracker main loop
    # -----------------------------
    @safe
    def track_loop(self):
        init_db(); init_multi_modal_db(); init_memory_decay_db()
        kb_listener, ms_listener = self.start_listeners()
        save_time = time.time()

        while not self.stop_event.is_set():
            window, interaction = self.get_active_window()
            self.log_session(window, interaction)

            # Audio
            self.latest_audio, _ = self.classify_audio_live()

            # OCR
            ocr_data = ocr_pipeline() or {}
            self.latest_ocr = {str(k): {"score": float(v.get("score",0.5)), "count":int(v.get("count",1))} for k,v in ocr_data.get("keywords", {}).items()}
            if self.latest_ocr: add_concepts(list(self.latest_ocr.keys()))

            # Webcam
            if USER_ALLOW_WEBCAM:
                frame = webcam_pipeline()
                faces, num_faces = self.face_detector.detect_faces(frame)
                self.latest_attention = int(num_faces)

            # Memory & reminders
            # [Compute memory scores and maybe notify here — can be refactored into a helper]

            # Intent
            intent_data = self.predict_intent_live(self.latest_ocr, self.latest_audio, self.latest_attention, interaction)

            # Knowledge graph
            add_edges(self.latest_ocr, self.latest_audio, intent_data.get("intent_label", "unknown"))

            # Multi-modal logging
            self.log_multi_modal(window, self.latest_ocr, self.latest_audio, self.latest_attention, interaction, intent_data["intent_label"], intent_data["confidence"])

            # Periodic save
            if time.time() - save_time > 300:
                self.save_graph()
                save_time = time.time()

            time.sleep(TRACK_INTERVAL)

    @safe
    def save_graph(self):
        os.makedirs("data", exist_ok=True)
        with open("data/knowledge_graph.pkl", "wb") as f:
            pickle.dump(self.graph, f)
        logger.info("Knowledge graph saved.")

# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    consent = input("Enable webcam attention tracking? (y/n): ").strip().lower() == "y"
    USER_ALLOW_WEBCAM = consent
    tracker = Tracker()
    tracker.track_loop()
