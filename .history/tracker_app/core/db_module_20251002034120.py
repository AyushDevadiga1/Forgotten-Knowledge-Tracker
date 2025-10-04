#core/__init__.py
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
