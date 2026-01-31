# core/db_module.py
"""
Database Initialization Module
------------------------------
Provides safe creation of session, multi-modal, and memory_decay tables.
Includes logging and type hints for traceability.
"""

import sqlite3
from config import DB_PATH
import logging
from typing import Optional
# core/db_module.py
import sqlite3
from config import DB_PATH
from datetime import datetime
# -----------------------------
# LOGGER SETUP
# -----------------------------
logging.basicConfig(
    filename="logs/db_module.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -----------------------------
# Initialize sessions table
# -----------------------------
def init_db(db_path: Optional[str] = None) -> None:
    """Session/activity logging table"""
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    try:
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
        logging.info("Sessions table initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize sessions table: {e}")
    finally:
        conn.close()


# -----------------------------
# Initialize multi-modal logs table
# -----------------------------
def init_multi_modal_db(db_path: Optional[str] = None) -> None:
    """Multi-modal logs: OCR, audio, intent, attention, interaction"""
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    try:
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
        conn.commit()
        logging.info("Multi-modal logs table initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize multi-modal logs table: {e}")
    finally:
        conn.close()


# -----------------------------
# Initialize memory decay table
# -----------------------------
def init_memory_decay_db(db_path: Optional[str] = None) -> None:
    """Track forgetting curve predictions"""
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS memory_decay (
                keyword TEXT,
                last_seen_ts TEXT,
                predicted_recall REAL,
                observed_usage INTEGER,
                updated_at TEXT
            )
        ''')
        conn.commit()
        logging.info("Memory decay table initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize memory_decay table: {e}")
    finally:
        conn.close()


def log_multi_modal_event(
    window_title: str = "",
    ocr_keywords: str = "",
    audio_label: str = "",
    attention_score: float = 0.0,
    interaction_rate: float = 0.0,
    intent_label: str = "",
    intent_confidence: float = 0.0,
    memory_score: float = 0.0,
    source_module: str = ""
):
    """
    Log any multi-modal event (OCR, audio, intent, memory) into multi_modal_logs table.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
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
        conn.close()
        logging.info(f"[DB Logger] Event logged from {source_module}: {window_title}")
    except Exception as e:
        logging.error(f"[DB Logger] Failed to log event from {source_module}: {e}")

# -----------------------------
# SELF-TEST
# -----------------------------
if __name__ == "__main__":
    init_db()
    init_multi_modal_db()
    init_memory_decay_db()
    print("✅ All tables initialized successfully (check logs/db_module.log).")
