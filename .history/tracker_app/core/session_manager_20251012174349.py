# core/session_manager.py
"""
Session Manager Module (IEEE-Ready v2)
---------------------------------------
- Creates and updates user sessions
- Automatic DB logging for each session update
- Tracks attention, audio, intent, interaction, memory, last review, next review
- Fully typed, traceable with logging, and DB-safe
"""

from datetime import datetime
from typing import Dict, Any
import logging
import sqlite3
from config import DB_PATH
from core.db_module import log_multi_modal_event

# ==============================
# LOGGER SETUP
# ==============================
logging.basicConfig(
    filename="logs/session_manager.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ==============================
# SESSION MANAGEMENT
# ==============================
def create_session() -> Dict[str, Any]:
    """Initialize a new session dictionary with default values."""
    session: Dict[str, Any] = {
        "window_title": "",
        "interaction_rate": 0,
        "ocr_keywords": [],
        "audio_label": "silence",
        "audio_confidence": 0.0,
        "attention_score": 0.0,
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


def update_session(session: Dict[str, Any], key: str, value: Any, log_db: bool = True) -> None:
    """
    Update a session field and optionally log the update to DB.
    """
    try:
        session[key] = value
        session["last_update"] = datetime.now()
        logging.info(f"Session updated: {key} = {value}")

        if log_db:
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
        logging.error(f"[SessionManager] Failed to update session: {e}", exc_info=True)


def log_session_to_db(session: Dict[str, Any]) -> None:
    """
    Save the complete session state to the 'sessions' table safely.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO sessions (
                    start_ts, end_ts, app_name, window_title, interaction_rate,
                    audio_label, intent_label, intent_confidence,
                    attention_score, memory_score, last_review, next_review
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.get("start_time", datetime.now()).isoformat(),
                session.get("last_update", datetime.now()).isoformat(),
                session.get("window_title", ""),
                session.get("window_title", ""),
                session.get("interaction_rate", 0),
                session.get("audio_label", ""),
                session.get("intent_label", ""),
                session.get("intent_confidence", 0.0),
                session.get("attention_score", 0.0),
                session.get("memory_score", 0.0),
                session.get("last_review", datetime.now()).isoformat(),
                session.get("next_review", datetime.now()).isoformat()
            ))
            logging.info("Full session logged to DB successfully")
    except Exception as e:
        logging.error(f"[SessionManager] Failed to log session to DB: {e}", exc_info=True)


# ==============================
# SELF-TEST
# ==============================
if __name__ == "__main__":
    session = create_session()
    update_session(session, "window_title", "Photosynthesis")
    update_session(session, "interaction_rate", 12)
    update_session(session, "ocr_keywords", ["chlorophyll", "light reaction"])
    update_session(session, "memory_score", 0.55)
    update_session(session, "next_review", datetime.now())
    log_session_to_db(session)

    print("✅ Session created and logged successfully")
    print(session)
