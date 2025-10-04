# session_manager.py

from datetime import datetime
from core.db_module import log_session_data

# -----------------------------
# Create a new session object
# -----------------------------
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

# -----------------------------
# Update session key with optional auto-save to DB
# -----------------------------
def update_session(session, key, value, save_to_db=False):
    session[key] = value
    session["last_update"] = datetime.now()
    if save_to_db:
        log_session_data(session)

# -----------------------------
# Finalize session and save to DB
# -----------------------------
def end_session(session):
    # Add optional end time
    session["end_time"] = datetime.now()
    log_session_data(session)
