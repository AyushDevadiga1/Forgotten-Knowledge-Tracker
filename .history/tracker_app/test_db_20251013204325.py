import sqlite3
from config import DB_PATH

def clear_all_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Clear sessions
        cursor.execute("DELETE FROM sessions")
        print("Cleared all sessions")

        # Clear multi-modal logs
        cursor.execute("DELETE FROM multi_modal_logs")
        print("Cleared all multi-modal logs")

        # Clear memory decay
        cursor.execute("DELETE FROM memory_decay")
        print("Cleared all memory decay entries")

        # Clear metrics / reminders
        cursor.execute("DELETE FROM metrics")
        print("Cleared all metrics/reminders")

        conn.commit()
        print("All table data cleared successfully.")
    except Exception as e:
        print(f"Error clearing data: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clear_all_data()
