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

def log_session(start_ts=None, end_ts=None, app_name=None, window_title=None, interaction_rate=0,
                audio_label=None, intent_label=None, intent_confidence=None):
    import sqlite3
    from config import DB_PATH
    from datetime import datetime

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    start_ts = start_ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    end_ts = end_ts or start_ts

    c.execute('''
        INSERT INTO sessions 
        (start_ts, end_ts, app_name, window_title, interaction_rate, audio_label, intent_label, intent_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (start_ts, end_ts, app_name, window_title, interaction_rate, audio_label, intent_label, intent_confidence))

    conn.commit()
    conn.close()

