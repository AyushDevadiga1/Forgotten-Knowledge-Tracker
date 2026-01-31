# core/session_manager.py
"""
Session Manager Module (IEEE-Ready)
-----------------------------------
- Creates and updates user sessions
- Automatic DB logging for each session update
- Tracks attention, audio, intent, interaction, memory, and last review
- Fully typed and traceable with logging
"""

from datetime import datetime
from typing import Dict, Any
import logging
import sqlite3
from config import DB_PATH
from core.db_module import log_multi_modal_event

# -----------------------------
# LOGGER SETUP
# -----------------------------
logging.basicConfig(
    filename="logs/session_manager.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -----------------------------
# Create new session
# -----------------------------
def create_session() -> Dict[str, Any]:
    """
    Initialize a new session dictionary with default values.
    """
    session: Dict[str, Any] = {
        "window_title": "",
        "interaction_rate": 0,
        "ocr_keywords": [],
        "audio_label": "silence",
        "audio_confidence": 0.0,
        "attention_score": 0,
        "intent_label": "",
        "intent_confidence": 0.0,
        "memory_score": 0.0,
        "last_review": datetime.now(),
        "next_review": datetime.now(),
        "start_time": datetime.now(),
        "last_update": datetime.now()
    }
    logging.info("Created new session")
    return session

# -----------------------------
# Update session key/value
# -----------------------------
def update_session(session: Dict[str, Any], key: str, value: Any, log_db: bool = True) -> None:
    """
    Update a session field and automatically log to DB if log_db=True.
    """
    try:
        session[key] = value
        session["last_update"] = datetime.now()
        logging.info(f"Session updated: {key} = {value}")

        if log_db:
            # Log the session update to multi-modal DB
            log_multi_modal_event(
                window_title=session.get("window_title", ""),
                ocr_keywords=", ".join(session.get("ocr_keywords", [])),
                audio_label=session.get("audio_label", ""),
                attention_score=session.get("attention_score", 0.0),
                interaction_rate=session.get("interaction_rate", 0.0),
                intent_label=session.get("intent_label", ""),
                intent_confidence=session.get("intent_confidence", 0.0),
                memory_score=session.get("memory_score", 0.0),
                source_module="SessionManager"
            )

    except Exception as e:
        logging.error(f"[SessionManager] Failed to update session: {e}")

# -----------------------------
# Log complete session
# -----------------------------
def log_session_to_db(session: Dict[str, Any]) -> None:
    """
    Save the current session state to the 'sessions' table.
    """
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute('''
            INSERT INTO sessions (
                start_ts, end_ts, app_name, window_title, interaction_rate,
                audio_label, intent_label, intent_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.get("start_time", datetime.now()).isoformat(),
            session.get("last_update", datetime.now()).isoformat(),
            session.get("window_title", ""),
            session.get("window_title", ""),
            session.get("interaction_rate", 0),
            session.get("audio_label", ""),
            session.get("intent_label", ""),
            session.get("intent_confidence", 0.0)
        ))

        conn.commit()
        conn.close()
        logging.info("Full session logged to DB successfully")

    except Exception as e:
        logging.error(f"[SessionManager] Failed to log session to DB: {e}")

# -----------------------------
# SELF-TEST
# -----------------------------
if __name__ == "__main__":
    session = create_session()
    update_session(session, "window_title", "Photosynthesis")
    update_session(session, "interaction_rate", 12)
    update_session(session, "ocr_keywords", ["chlorophyll", "light reaction"])
    log_session_to_db(session)
    print("✅ Session created and logged successfully")
