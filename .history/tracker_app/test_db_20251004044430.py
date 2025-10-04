import sqlite3
from config import DB_PATH

def create_memory_decay_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create table only if it doesn't exist
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
    print("memory_decay table is ready.")

if __name__ == "__main__":
    create_memory_decay_table()
