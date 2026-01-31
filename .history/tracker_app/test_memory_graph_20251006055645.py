# test_add_column.py
import sqlite3
from config import DB_PATH

def ensure_column_exists(table_name: str, column_name: str, column_type: str = "TEXT", default_value: str = "Unknown"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = [info[1] for info in cursor.fetchall()]
    
    if column_name not in columns:
        print(f"[INFO] Column '{column_name}' not found in '{table_name}'. Adding it now...")
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT '{default_value}';")
        conn.commit()
        print(f"[SUCCESS] Column '{column_name}' added successfully.")
    else:
        print(f"[INFO] Column '{column_name}' already exists in '{table_name}'.")

    conn.close()

if __name__ == "__main__":
    ensure_column_exists("multi_modal_logs", "source_module")
