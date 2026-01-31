import sqlite3

DB_PATH = "tracker.db"  # adjust if needed
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(multi_modal_logs)")
columns = cursor.fetchall()
for col in columns:
    print(col)
conn.close()
