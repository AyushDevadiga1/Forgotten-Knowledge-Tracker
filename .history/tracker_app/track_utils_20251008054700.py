# tracker_utils.py
import sqlite3
from datetime import datetime
from config import DB_PATH
import logging

# -----------------------------
# Logger setup (optional if already in db_module.py)
# -----------------------------
logging.basicConfig(
    filename="logs/tracker_utils.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -----------------------------
# SESSION LOGGING
# -----------------------------
def log_session(app_name: str, window_title: str, interaction_rate: float = 0.0,
                audio_label: str = "", intent_label: str = "", intent_confidence: float = 0.0,
                start_ts: datetime = None, end_ts: datetime = None):
    start_ts = start_ts or datetime.now()
    end_ts = end_ts or datetime.now()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO sessions (start_ts, end_ts, app_name, window_title, interaction_rate,
                                  audio_label, intent_label, intent_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (start_ts, end_ts, app_name, window_title, interaction_rate,
              audio_label, intent_label, intent_confidence))
        conn.commit()
        conn.close()
        logging.info(f"[Session Logger] Logged session for {window_title}")
    except Exception as e:
        logging.error(f"[Session Logger] Failed to log session: {e}")

# -----------------------------
# MULTI-MODAL EVENT LOGGING
# -----------------------------
def log_event(window_title: str = "", ocr_keywords: str = "", audio_label: str = "",
              attention_score: float = 0.0, interaction_rate: float = 0.0,
              intent_label: str = "", intent_confidence: float = 0.0,
              memory_score: float = 0.0, source_module: str = "", session_id: str = ""):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO multi_modal_logs (timestamp, window_title, ocr_keywords, audio_label,
                                          attention_score, interaction_rate, intent_label,
                                          intent_confidence, memory_score, source_module, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), window_title, ocr_keywords, audio_label,
              attention_score, interaction_rate, intent_label,
              intent_confidence, memory_score, source_module, session_id))
        conn.commit()
        conn.close()
        logging.info(f"[Event Logger] Logged event from {source_module}")
    except Exception as e:
        logging.error(f"[Event Logger] Failed to log event from {source_module}: {e}")

# -----------------------------
# METRICS / MEMORY DECAY UPDATE
# -----------------------------
def update_metric(concept: str, memory_score: float, next_review_time: datetime):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO metrics (concept, memory_score, next_review_time)
            VALUES (?, ?, ?)
        ''', (concept, memory_score, next_review_time))
        conn.commit()
        conn.close()
        logging.info(f"[Metrics] Updated metric for concept: {concept}")
    except Exception as e:
        logging.error(f"[Metrics] Failed to update metric for {concept}: {e}")
