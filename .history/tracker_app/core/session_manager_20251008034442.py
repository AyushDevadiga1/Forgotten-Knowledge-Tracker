import sqlite3
from datetime import datetime
from config import DB_PATH
from typing import Dict, Any, Optional
import logging

logging.basicConfig(filename="logs/session_manager.log", level=logging.INFO)

def create_session() -> Dict[str, Any]:
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

def update_session(session: Dict[str, Any], key: str, value: Any) -> None:
    session[key] = value
    session["last_update"] = datetime.now()
    logging.info(f"Session updated: {key}={value}")

def log_session(
    start_ts: Optional[datetime] = None,
    end_ts: Optional[datetime] = None,
    app_name: Optional[str] = None,
    window_title: Optional[str] = None,
    interaction_rate: int = 0,
    audio_label: Optional[str] = None,
    intent_label: Optional[str] = None,
    intent_confidence: Optional[float] = None
) -> None:
    try:
        start_ts = start_ts or datetime.now()
        end_ts = end_ts or start_ts

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO sessions 
                (start_ts, end_ts, app_name, window_title, interaction_rate, audio_label, intent_label, intent_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                start_ts.strftime("%Y-%m-%d %H:%M:%S"),
                end_ts.strftime("%Y-%m-%d %H:%M:%S"),
                app_name,
                window_title,
                interaction_rate,
                audio_label,
                intent_label,
                intent_confidence
            ))
        logging.info(f"Session logged: {window_title}, interaction_rate={interaction_rate}")
    except Exception as e:
        logging.error(f"Failed to log session: {e}")
