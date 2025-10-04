# core/db_module.py

import sqlite3
from datetime import datetime
from config import DB_PATH

# Optional: encryption
try:
    from cryptography.fernet import Fernet
    USE_ENCRYPTION = True
    # You can store key in config.py or environment variable
    from config import ENCRYPTION_KEY
except ImportError:
    USE_ENCRYPTION = False

# -----------------------------
# DB Initialization
# -----------------------------
def init_db():
    """
    Initialize the SQLite database with required tables.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Table for session/activity logging
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_ts TEXT,
                    end_ts TEXT,
                    app_name TEXT,
                    window_title TEXT,
                    interaction_rate REAL
                )''')

    # Optional metrics table
    c.execute('''CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept TEXT,
                    memory_score REAL,
                    next_review_time TEXT
                )''')

    conn.commit()
    conn.close()

# -----------------------------
# Encryption Helpers
# -----------------------------
def encrypt_data(data: str) -> str:
    if USE_ENCRYPTION:
        f = Fernet(ENCRYPTION_KEY)
        return f.encrypt(data.encode()).decode()
    return data

def decrypt_data(data: str) -> str:
    if USE_ENCRYPTION:
        f = Fernet(ENCRYPTION_KEY)
        return f.decrypt(data.encode()).decode()
    return data

# -----------------------------
# Log session using session_data
# -----------------------------
def log_session_data(session_data: dict):
    """
    Write a snapshot of session_data to the DB.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    ts = session_data.get("last_update", datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    app_name = session_data.get("window_title", "")
    window_title = session_data.get("window_title", "")
    interaction_rate = session_data.get("interaction_rate", 0)

    # Optional encryption
    app_name_enc = encrypt_data(app_name)
    window_title_enc = encrypt_data(window_title)

    c.execute("""INSERT INTO sessions
                 (start_ts, end_ts, app_name, window_title, interaction_rate)
                 VALUES (?, ?, ?, ?, ?)""",
              (ts, ts, app_name_enc, window_title_enc, interaction_rate))
    conn.commit()
    conn.close()

# -----------------------------
# Optional: log metrics for memory model
# -----------------------------
def log_metric(concept: str, memory_score: float, next_review_time: datetime):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    concept_enc = encrypt_data(concept)
    next_review_str = next_review_time.strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""INSERT INTO metrics
                 (concept, memory_score, next_review_time)
                 VALUES (?, ?, ?)""",
              (concept_enc, memory_score, next_review_str))
    conn.commit()
    conn.close()
