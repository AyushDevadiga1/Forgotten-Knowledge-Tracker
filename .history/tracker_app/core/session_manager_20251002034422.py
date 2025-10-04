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
