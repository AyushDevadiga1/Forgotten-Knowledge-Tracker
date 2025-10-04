import sqlite3
from config import DB_PATH
from core.encryption_module import encrypt_data, decrypt_data

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Table for session/activity logging
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_ts TEXT,
                    end_ts TEXT,
                    app_name BLOB,
                    window_title BLOB,
                    interaction_rate REAL
                )''')
    conn.commit()
    conn.close()

def log_session_encrypted(start_ts, end_ts, app_name, window_title, interaction_rate):
    from core.encryption_module import encrypt_data
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""INSERT INTO sessions 
                 (start_ts, end_ts, app_name, window_title, interaction_rate) 
                 VALUES (?, ?, ?, ?, ?)""",
              (start_ts, end_ts, encrypt_data(app_name), encrypt_data(window_title), interaction_rate))
    conn.commit()
    conn.close()

def fetch_sessions_decrypted(limit=50):
    from core.encryption_module import decrypt_data
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT start_ts, end_ts, app_name, window_title, interaction_rate FROM sessions ORDER BY start_ts DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()

    # Decrypt app_name and window_title
    decrypted_rows = []
    for start, end, app, win, ir in rows:
        decrypted_rows.append((
            start,
            end,
            decrypt_data(app),
            decrypt_data(win),
            ir
        ))
    return decrypted_rows
