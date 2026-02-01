# core/db_module.py
import sqlite3
import os
from contextlib import contextmanager
from tracker_app.config import DB_PATH

@contextmanager
def get_db_connection():
    """Context manager for database connections - ensures proper cleanup"""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception as e:
            print(f"Error closing database connection: {e}")

def ensure_db_directory():
    """Ensure the database directory exists"""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

def init_db():
    """Initialize sessions table"""
    ensure_db_directory()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_ts TEXT NOT NULL,
                end_ts TEXT NOT NULL,
                app_name TEXT,
                window_title TEXT,
                interaction_rate REAL DEFAULT 0,
                interaction_count INTEGER DEFAULT 0,
                audio_label TEXT,
                intent_label TEXT,
                intent_confidence REAL DEFAULT 0.0
            )
        ''')
        
        # Create index for better performance
        c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_ts ON sessions(start_ts)')
        
        conn.commit()
        conn.close()
        print("Sessions table initialized successfully.")
    except Exception as e:
        print(f"Error initializing sessions table: {e}")

def init_multi_modal_db():
    """Initialize multi-modal logs table"""
    ensure_db_directory()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute(''' 
            CREATE TABLE IF NOT EXISTS multi_modal_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                window_title TEXT,
                ocr_keywords TEXT,
                audio_label TEXT,
                attention_score REAL DEFAULT 0,
                interaction_rate REAL DEFAULT 0,
                intent_label TEXT,
                intent_confidence REAL DEFAULT 0.0,
                memory_score REAL DEFAULT 0.0
            )
        ''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_mm_timestamp ON multi_modal_logs(timestamp)')
        
        conn.commit()
        conn.close()
        print("Multi-modal logs table initialized successfully.")
    except Exception as e:
        print(f"Error initializing multi-modal logs table: {e}")

def init_memory_decay_db():
    """Initialize memory decay table"""
    ensure_db_directory()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS memory_decay (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                last_seen_ts TEXT NOT NULL,
                predicted_recall REAL DEFAULT 0.0,
                observed_usage INTEGER DEFAULT 1,
                updated_at TEXT NOT NULL
            )
        ''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_memory_keyword ON memory_decay(keyword)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_memory_ts ON memory_decay(last_seen_ts)')
        
        conn.commit()
        conn.close()
        print("Memory decay table initialized successfully.")
    except Exception as e:
        print(f"Error initializing memory decay table: {e}")

def init_metrics_db():
    """Initialize metrics table for reminders"""
    ensure_db_directory()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept TEXT NOT NULL,
                next_review_time TEXT,
                memory_score REAL DEFAULT 0.0,
                last_updated TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Metrics table initialized successfully.")
    except Exception as e:
        print(f"Error initializing metrics table: {e}")

def init_all_databases():
    """Initialize all database tables"""
    init_db()
    init_multi_modal_db()
    init_memory_decay_db()
    init_metrics_db()
    print("All database tables initialized.")

if __name__ == "__main__":
    init_all_databases()