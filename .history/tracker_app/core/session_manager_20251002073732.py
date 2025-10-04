# core/session_manager.py

from datetime import datetime

def create_session():
    return {
        "window_title": "",
        "interaction_rate": 0,
        "ocr_keywords": [],
        "audio_label": "silence",
        "attention_score": 0,
        "intent_label": "",
        "intent_confidence": 0.0,
        "start_time": datetime.now(),
        "last_update": datetime.now()
    }

def update_session(session, key, value):
    session[key] = value
    session["last_update"] = datetime.now()
# core/session_manager.py
import sqlite3
from config import DB_PATH

def log_session(window_title, interaction_count, audio_label, intent_label):
    """Simple session logging to DB."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO sessions (window_title, interaction_count, audio_label, intent_label)
        VALUES (?, ?, ?, ?)
    """, (window_title, interaction_count, audio_label, intent_label))
    conn.commit()
    conn.close()
