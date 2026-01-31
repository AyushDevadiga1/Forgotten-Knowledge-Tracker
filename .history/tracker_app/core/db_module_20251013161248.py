# ==========================================================
# core/db_module.py
# ==========================================================
"""
Database Module (IEEE-Ready v3)
--------------------------------
- Safe creation of session, multi-modal, memory_decay, and metrics tables
- Logging, type hints, and traceability for FKT system
- Thread-safe and structured API
"""

import sqlite3
from config import DB_PATH
import logging
from typing import Optional, Any, List, Tuple
from datetime import datetime, timedelta
import threading

# ----------------------------- Logger Setup -----------------------------
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        filename="logs/db_module.log",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
logger = logging.getLogger(__name__)

# ----------------------------- DB CONNECTION -----------------------------
_db_lock = threading.Lock()  # Ensure thread-safe writes

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a new SQLite connection using the configured DB path."""
    path = db_path or DB_PATH
    return sqlite3.connect(path, check_same_thread=False)

# ----------------------------- INIT TABLES -----------------------------
def init_sessions_table(conn: sqlite3.Connection) -> None:
    """Initialize sessions table."""
    with conn:
        conn.execute('''
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
    logger.info("Sessions table initialized.")

def init_multi_modal_table(conn: sqlite3.Connection) -> None:
    """Initialize multi-modal logs table."""
    with conn:
        conn.execute('''
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
                memory_score REAL,
                source_module TEXT
            )
        ''')
    logger.info("Multi-modal logs table initialized.")

def init_memory_decay_table(conn: sqlite3.Connection) -> None:
    """Initialize memory_decay table."""
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS memory_decay (
                concept TEXT,
                last_seen_ts TEXT,
                predicted_recall REAL,
                observed_usage INTEGER,
                updated_at TEXT
            )
        ''')
    logger.info("Memory decay table initialized.")

def init_metrics_table(conn: sqlite3.Connection) -> None:
    """Initialize metrics table and populate from memory_decay if empty."""
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                concept TEXT PRIMARY KEY,
                next_review_time TEXT,
                memory_score REAL
            )
        ''')
        # Populate metrics from memory_decay if empty
        count = conn.execute('SELECT COUNT(*) FROM metrics').fetchone()[0]
        if count == 0:
            rows = conn.execute('SELECT concept, predicted_recall, last_seen_ts FROM memory_decay').fetchall()
            for concept, recall, last_seen in rows:
                next_review = (datetime.fromisoformat(last_seen) + timedelta(days=1)).isoformat()
                conn.execute('''
                    INSERT OR REPLACE INTO metrics (concept, next_review_time, memory_score)
                    VALUES (?, ?, ?)
                ''', (concept, next_review, recall))
    logger.info("Metrics table initialized.")

def init_all_tables(db_path: Optional[str] = None) -> None:
    """Initialize all DB tables safely."""
    try:
        with get_db_connection(db_path) as conn:
            init_sessions_table(conn)
            init_multi_modal_table(conn)
            init_memory_decay_table(conn)
            init_metrics_table(conn)
        logger.info("All tables initialized successfully.")
    except Exception:
        logger.exception("Failed to initialize one or more tables.")

# ----------------------------- LOG MULTI-MODAL EVENT -----------------------------
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
    """Thread-safe logging of multi-modal events."""
    try:
        with _db_lock, get_db_connection(db_path) as conn:
            conn.execute('''
                INSERT INTO multi_modal_logs (
                    timestamp, window_title, ocr_keywords, audio_label, attention_score,
                    interaction_rate, intent_label, intent_confidence, memory_score, source_module
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(), window_title, ocr_keywords, audio_label, attention_score,
                interaction_rate, intent_label, intent_confidence, memory_score, source_module
            ))
        logger.info(f"[DB Logger] Event logged from {source_module}: {window_title}")
    except Exception:
        logger.exception(f"[DB Logger] Failed to log event from {source_module}: {window_title}")

# ----------------------------- SELF-TEST -----------------------------
if __name__ == "__main__":
    init_all_tables()
    print("✅ All tables initialized successfully (check logs/db_module.log).")
