import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Get all tables
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in c.fetchall()]
print("Tables in DB:", tables)

# Show columns for each table
for table in tables:
    c.execute(f"PRAGMA table_info({table})")
    cols = c.fetchall()
    print(f"\nColumns in '{table}':")
    for col in cols:
        print(f" - {col[1]} ({col[2]})")

conn.close()
