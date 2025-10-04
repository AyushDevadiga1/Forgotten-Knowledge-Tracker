import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Check existing columns
c.execute("PRAGMA table_info(sessions)")
columns = [col[1] for col in c.fetchall()]

# Add missing columns one by one
if 'audio_label' not in columns:
    c.execute("ALTER TABLE sessions ADD COLUMN audio_label TEXT")
if 'intent_label' not in columns:
    c.execute("ALTER TABLE sessions ADD COLUMN intent_label TEXT")
if 'intent_confidence' not in columns:
    c.execute("ALTER TABLE sessions ADD COLUMN intent_confidence REAL")

conn.commit()
conn.close()
print("Migrated sessions table to include multi-modal columns.")
