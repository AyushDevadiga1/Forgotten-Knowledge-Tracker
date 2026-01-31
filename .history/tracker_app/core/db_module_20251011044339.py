# core/db_module.py
"""
Database Initialization Module
------------------------------
Provides safe creation of session, multi-modal, and memory_decay tables.
Includes logging, type hints, and traceability for FKT system.
"""

import sqlite3
from config import DB_PATH
import logging
from typing import Optional
from datetime import datetime

# -----------------------------
# LOGGER SETUP
# -----------------------------
logging.basicConfig(
    filename="logs/db_module.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------------
# DB CONNECTION HELPER
# -----------------------------
def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a new SQLite connection using the configured DB path."""
    path = db_path or DB_PATH
    return sqlite3.connect(path)

# -----------------------------
# Initialize sessions table
# -----------------------------
def init_db(db_path: Optional[str] = None) -> None:
    """Session/activity logging table"""
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_ts TEXT,
                    end_ts TEXT,
                    app_name TEXT,
                    window_title TEXT,
                    interaction_rate REAL,
                    interaction_count INTEGER DEFAULT 0,
                    audio_label TEXT,
                    intent_label TEXT,
                    intent_confidence REAL
                )
            ''')
            conn.commit()
        logger.info("Sessions table initialized successfully.")
    except Exception:
        logger.exception("Failed to initialize sessions table.")

# -----------------------------
# Initialize multi-modal logs table
# -----------------------------
def init_multi_modal_db(db_path: Optional[str] = None) -> None:
    """Multi-modal logs: OCR, audio, intent, attention, interaction"""
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS multi_modal_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    window_title TEXT,
                    ocr_keywords TEXT,
                    audio_label TEXT,
                    attention_score REAL,
                    interaction_rate REAL,
                    intent_label TEXT,
                    intent_confidence REAL,
                    memory_score REAL
                )
            ''')
            # Add `source_module` column if missing
            c.execute("PRAGMA table_info(multi_modal_logs)")
            columns = [col[1] for col in c.fetchall()]
            if "source_module" not in columns:
                c.execute("ALTER TABLE multi_modal_logs ADD COLUMN source_module TEXT")
            conn.commit()
        logger.info("Multi-modal logs table initialized/updated successfully.")
    except Exception:
        logger.exception("Failed to initialize/update multi-modal logs table.")

# -----------------------------
# Initialize memory decay table
# -----------------------------
def init_memory_decay_db(db_path: Optional[str] = None) -> None:
    """Track forgetting curve predictions"""
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS memory_decay (
                    concept TEXT,
                    last_seen_ts TEXT,
                    predicted_recall REAL,
                    observed_usage INTEGER,
                    updated_at TEXT
                )
            ''')
            conn.commit()
        logger.info("Memory decay table initialized successfully.")
    except Exception:
        logger.exception("Failed to initialize memory_decay table.")

# -----------------------------
# Log a multi-modal event
# -----------------------------
def log_multi_modal_event(
    window_title: str = "",
    ocr_keywords: str = "",
    audio_label: str = "",
    attention_score: float = 0.0,
    interaction_rate: float = 0.0,
    intent_label: str = "",
    intent_confidence: float = 0.0,
    memory_score: float = 0.0,
    source_module: str = "",
    db_path: Optional[str] = None
) -> None:
    """Log any multi-modal event (OCR, audio, intent, memory) into multi_modal_logs table."""
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO multi_modal_logs (
                    timestamp, window_title, ocr_keywords, audio_label, attention_score,
                    interaction_rate, intent_label, intent_confidence, memory_score, source_module
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(), window_title, ocr_keywords, audio_label, attention_score,
                interaction_rate, intent_label, intent_confidence, memory_score, source_module
            ))
            conn.commit()
        logger.info(f"[DB Logger] Event logged from {source_module}: {window_title}")
    except Exception:
        logger.exception(f"[DB Logger] Failed to log event from {source_module}: {window_title}")

# -----------------------------
# SELF-TEST
# -----------------------------
if __name__ == "__main__":
    init_db()
    init_multi_modal_db()
    init_memory_decay_db()
    print("✅ All tables initialized successfully (check logs/db_module.log).")
