import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Check if column exists
c.execute("PRAGMA table_info(sessions)")
columns = [col[1] for col in c.fetchall()]

if 'interaction_count' not in columns:
    c.execute("ALTER TABLE sessions ADD COLUMN interaction_count INTEGER DEFAULT 0")
    print("Added 'interaction_count' column to sessions table.")

conn.commit()
conn.close()
