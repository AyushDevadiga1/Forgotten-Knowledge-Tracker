import sqlite3
from config import DB_PATH

def preview_table(table_name, limit=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        rows = c.fetchall()
        if rows:
            print(f"\n--- Sample rows from '{table_name}' ---")
            for row in rows:
                print(row)
        else:
            print(f"\n'{table_name}' is empty.")
    except Exception as e:
        print(f"Error fetching from {table_name}: {e}")
    finally:
        conn.close()

tables = ['sessions', 'multi_modal_logs', 'memory_decay', 'metrics']

for table in tables:
    preview_table(table)
