# ==========================================================
# core/db_module.py | FKT v4.0 Async & Multi-Modal Ready
# ==========================================================
"""
Database Module (IEEE-Ready v4.0)
----------------------------------
- Thread-safe & async-safe DB operations
- Tables: sessions, multi_modal_logs, memory_decay, metrics
- Memory decay & metrics logging APIs
- Full logging & error traceability
"""

import sqlite3
import logging
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from config import DB_PATH

# ----------------------------- Logger Setup -----------------------------
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        filename="logs/db_module.log",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
logger = logging.getLogger(__name__)

# ----------------------------- Thread-Safe DB -----------------------------
_db_lock = threading.Lock()

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a new SQLite connection using the configured DB path."""
    path = db_path or DB_PATH
    return sqlite3.connect(path, check_same_thread=False)

# ----------------------------- Table Initialization -----------------------------
def init_sessions_table(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS sessions (
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
        )''')
    logger.info("Sessions table initialized.")

def init_db(conn: Optional[sqlite3.Connection] = None, db_path: Optional[str] = None) -> None:
    """Initialize all DB tables safely (renamed from init_all_tables)."""
    if conn is None:
        with get_db_connection(db_path) as conn:
            init_sessions_table(conn)
            init_multi_modal_db(conn)
            init_memory_decay_db(conn)
            init_metrics_table(conn)
    else:
        init_sessions_table(conn)
        init_multi_modal_db(conn)
        init_memory_decay_db(conn)
        init_metrics_table(conn)
    logger.info("All tables initialized successfully.")

def init_multi_modal_db(conn: sqlite3.Connection) -> None:
    """Initialize multi-modal logs table (renamed from init_multi_modal_table)."""
    with conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS multi_modal_logs (
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
        )''')
    logger.info("Multi-modal logs table initialized.")

def init_memory_decay_db(conn: sqlite3.Connection) -> None:
    """Initialize memory decay table (renamed from init_memory_decay_table)."""
    with conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS memory_decay (
            concept TEXT PRIMARY KEY,
            last_seen_ts TEXT,
            predicted_recall REAL,
            observed_usage INTEGER,
            updated_at TEXT
        )''')
    logger.info("Memory decay table initialized.")

def init_metrics_table(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS metrics (
            concept TEXT PRIMARY KEY,
            next_review_time TEXT,
            memory_score REAL
        )''')
    logger.info("Metrics table initialized.")

# ----------------------------- Logging Functions -----------------------------
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.utcnow().isoformat(), window_title, ocr_keywords, audio_label,
                attention_score, interaction_rate, intent_label, intent_confidence,
                memory_score, source_module
            ))
        logger.info(f"[DB Logger] Event logged from {source_module}: {window_title}")
    except Exception:
        logger.exception(f"[DB Logger] Failed to log event from {source_module}: {window_title}")

async def log_multi_modal_event_async(*args, **kwargs) -> None:
    """Async wrapper for non-blocking logging."""
    await asyncio.to_thread(log_multi_modal_event, *args, **kwargs)

# ----------------------------- Memory Decay -----------------------------
def log_memory_decay(
    concept: str,
    predicted_recall: float,
    observed_usage: int = 1,
    last_seen_ts: Optional[str] = None,
    db_path: Optional[str] = None
) -> None:
    last_seen_ts = last_seen_ts or datetime.utcnow().isoformat()
    try:
        with _db_lock, get_db_connection(db_path) as conn:
            conn.execute('''
                INSERT INTO memory_decay (concept, last_seen_ts, predicted_recall, observed_usage, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(concept) DO UPDATE SET
                    last_seen_ts=excluded.last_seen_ts,
                    predicted_recall=excluded.predicted_recall,
                    observed_usage=memory_decay.observed_usage + excluded.observed_usage,
                    updated_at=excluded.updated_at
            ''', (concept, last_seen_ts, predicted_recall, observed_usage, datetime.utcnow().isoformat()))
        logger.info(f"[Memory] Logged decay for concept '{concept}'")
    except Exception:
        logger.exception(f"[Memory] Failed to log decay for concept '{concept}'")

# ----------------------------- Metrics -----------------------------
def update_metric(
    concept: str,
    next_review_time: str,
    memory_score: float,
    db_path: Optional[str] = None
) -> None:
    """Insert or update a concept's metric."""
    try:
        with _db_lock, get_db_connection(db_path) as conn:
            conn.execute('''
                INSERT INTO metrics (concept, next_review_time, memory_score)
                VALUES (?, ?, ?)
                ON CONFLICT(concept) DO UPDATE SET
                    next_review_time=excluded.next_review_time,
                    memory_score=excluded.memory_score
            ''', (concept, next_review_time, memory_score))
        logger.info(f"[Metrics] Updated metric for '{concept}'")
    except Exception:
        logger.exception(f"[Metrics] Failed to update metric for '{concept}'")

# ----------------------------- Self-Test -----------------------------
if __name__ == "__main__":
    init_db()
    print("✅ FKT DB Module v4.0 initialized (check logs/db_module.log).")
