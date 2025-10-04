#core/db_module
import sqlite3
from config import DB_PATH

def init_db():
    """Session/activity logging"""
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()

    
def init_multi_modal_db():
    """Multi-modal logs: OCR, audio, intent, attention, interaction"""
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()


def init_memory_decay_db():
    """Track forgetting curve predictions"""
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()
