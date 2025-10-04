import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Remove rows where window_title is NULL or empty
c.execute("DELETE FROM sessions WHERE window_title IS NULL OR TRIM(window_title) = ''")
conn.commit()
conn.close()
print("✅ Empty/NULL window_title entries removed.")
