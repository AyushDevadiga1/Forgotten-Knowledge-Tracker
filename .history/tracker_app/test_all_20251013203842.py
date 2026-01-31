import sqlite3
from config import DB_PATH

def clear_test_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    tables = ["sessions", "multi_modal_logs", "memory_decay", "metrics"]

    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
            print(f"All data cleared from table: {table}")
        except Exception as e:
            print(f"Error clearing table {table}: {e}")

    conn.commit()
    conn.close()
    print("Database cleared of all test data.")

if __name__ == "__main__":
    clear_test_data()
