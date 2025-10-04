import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

try:
    c.execute("ALTER TABLE sessions ADD COLUMN interaction_count INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    # Column already exists
    pass

conn.commit()
conn.close()
