import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH

def clear_test_data_safely():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Define a safe filter: last 7 days or 'test' keywords/app names
    cutoff_date = datetime.now() - timedelta(days=7)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Sessions
        cursor.execute("""
            DELETE FROM sessions
            WHERE start_ts >= ? OR app_name LIKE '%test%' OR intent_label LIKE '%test%'
        """, (cutoff_str,))
        print("Cleared test sessions")

        # Multi-modal logs
        cursor.execute("""
            DELETE FROM multi_modal_logs
            WHERE timestamp >= ? OR window_title LIKE '%test%' OR intent_label LIKE '%test%'
        """, (cutoff_str,))
        print("Cleared test multi-modal logs")

        # Memory decay
        cursor.execute("""
            DELETE FROM memory_decay
            WHERE keyword LIKE '%test%'
        """)
        print("Cleared test memory decay entries")

        # Metrics / Reminders
        cursor.execute("""
            DELETE FROM metrics
            WHERE concept LIKE '%test%'
        """)
        print("Cleared test metrics/reminders")

        conn.commit()
        print("Safe cleanup completed.")
    except Exception as e:
        print(f"Error clearing test data safely: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clear_test_data_safely()
