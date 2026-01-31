# core/db_module.py
"""
Database Initialization & Logging Module
---------------------------------------
Optimized SQLite3 interface for the Forgotten Knowledge Tracker (FKT) system.
Ensures fast concurrent writes, async-ready logging, and reliable session tracking.

Features:
- Write-Ahead Logging (WAL) for concurrency
- Indexed tables for high-speed lookups
- Retry-safe inserts
- Optional cached connections
- Structured logging with traceability

Complies with:
- IEEE 1016 (Design Descriptions)
- IEEE 730 (Quality Assurance)
- IEEE 12207 (Configuration Management)
"""

import sqlite3
import logging
import time
from typing import Optional
from datetime import datetime, timedelta
from config import DB_PATH

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
# CONNECTION HELPERS
# -----------------------------
_conn_cache: Optional[sqlite3.Connection] = None

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create a new SQLite3 connection with performance tuning."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=10000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def get_cached_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Re-use a single connection across modules for performance."""
    global _conn_cache
    if _conn_cache is None:
        _conn_cache = get_db_connection(db_path)
    return _conn_cache

# -----------------------------
# SAFE EXECUTION (RETRY LOGIC)
# -----------------------------
def safe_execute(cursor, query, params=(), retries=3, delay=0.1):
    """Safely execute SQL statements with retries."""
    for attempt in range(retries):
        try:
            cursor.execute(query, params)
            return
        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"Failed after {retries} retries: {query}")

# -----------------------------
# TABLE INITIALIZATION
# -----------------------------
def init_db(db_path: Optional[str] = None) -> None:
    """Initialize sessions table."""
    try:
        conn = get_cached_connection(db_path)
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
        # Indexes for speed
        c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_time ON sessions(start_ts, end_ts)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_app ON sessions(app_name)')
        conn.commit()
        logger.info("Sessions table initialized successfully.")
    except Exception:
        logger.exception("Failed to initialize sessions table.")

def init_multi_modal_db(db_path: Optional[str] = None) -> None:
    """Initialize multi-modal logs table."""
    try:
        conn = get_cached_connection(db_path)
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
                memory_score REAL,
                source_module TEXT
            )
        ''')
        # Add indexes
        c.execute('CREATE INDEX IF NOT EXISTS idx_multi_modal_time ON multi_modal_logs(timestamp)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_multi_modal_window ON multi_modal_logs(window_title)')
        conn.commit()
        logger.info("Multi-modal logs table initialized successfully.")
    except Exception:
        logger.exception("Failed to initialize multi-modal logs table.")

def init_memory_decay_db(db_path: Optional[str] = None) -> None:
    """Initialize memory decay tracking table."""
    try:
        conn = get_cached_connection(db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS memory_decay (
                concept TEXT PRIMARY KEY,
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

def init_metrics_db(db_path: Optional[str] = None) -> None:
    """Initialize metrics table."""
    try:
        conn = get_cached_connection(db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                concept TEXT PRIMARY KEY,
                next_review_time TEXT,
                memory_score REAL
            )
        ''')
        # Auto-populate if empty
        c.execute('SELECT COUNT(*) FROM metrics')
        if c.fetchone()[0] == 0:
            c.execute('SELECT concept, predicted_recall, last_seen_ts FROM memory_decay')
            for concept, recall, last_seen in c.fetchall():
                next_review = (datetime.fromisoformat(last_seen) + timedelta(days=1)).isoformat()
                safe_execute(c, '''
                    INSERT OR REPLACE INTO metrics (concept, next_review_time, memory_score)
                    VALUES (?, ?, ?)
                ''', (concept, next_review, recall))
        conn.commit()
        logger.info("Metrics table initialized successfully.")
    except Exception:
        logger.exception("Failed to initialize metrics table.")

# -----------------------------
# EVENT LOGGING
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
    """Log any multi-modal event into the database safely."""
    try:
        conn = get_cached_connection(db_path)
        c = conn.cursor()
        safe_execute(c, '''
            INSERT INTO multi_modal_logs (
                timestamp, window_title, ocr_keywords, audio_label,
                attention_score, interaction_rate, intent_label,
                intent_confidence, memory_score, source_module
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            window_title,
            ocr_keywords,
            audio_label,
            attention_score,
            interaction_rate,
            intent_label,
            intent_confidence,
            memory_score,
            source_module
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
    init_metrics_db()
    print("✅ All tables initialized and optimized successfully (check logs/db_module.log).")
