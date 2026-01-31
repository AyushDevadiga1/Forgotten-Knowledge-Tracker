import sqlite3

from config import DB_PATH  # adjust if needed
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(multi_modal_logs)")
columns = cursor.fetchall()
for col in columns:
    print(col)
conn.close()
