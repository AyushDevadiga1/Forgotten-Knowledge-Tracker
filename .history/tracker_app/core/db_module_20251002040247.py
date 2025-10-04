#core/db_module.py
import sqlite3
from config import DB_PATH

def init_db():
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
    conn.commit()
    conn.close()
def init_multi_modal_db():
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
            intent_confidence REAL
        )
    ''')

    conn.commit()
    conn.close()