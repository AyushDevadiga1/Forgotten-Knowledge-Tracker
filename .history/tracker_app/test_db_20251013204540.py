import sqlite3
from config import DB_PATH

def reset_all_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        tables = ["sessions", "multi_modal_logs", "memory_decay", "metrics"]
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")  # reset AUTOINCREMENT
            print(f"Cleared table: {table}")

        conn.commit()
        # Optional: reclaim disk space
        cursor.execute("VACUUM")
        print("Database vacuumed. All data removed and AUTOINCREMENT reset.")
    except Exception as e:
        print(f"Error resetting tables: {e}")
    finally:
        conn.close()

if __name__ == "__main__":a
    reset_all_tables()
