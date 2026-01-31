import sqlite3
from config import DB_PATH
import pandas as pd

def test_memory_decay():
    conn = sqlite3.connect(DB_PATH)
    try:
        # List all columns in memory_decay
        c = conn.cursor()
        c.execute("PRAGMA table_info(memory_decay)")
        cols = c.fetchall()
        print("Columns in memory_decay table:")
        for col in cols:
            print(col)

        # Fetch all data
        df = pd.read_sql("SELECT * FROM memory_decay", conn)
        print("\nSample data from memory_decay:")
        print(df.head())

        # Test fetch_decay logic
        df_test = pd.read_sql(
            "SELECT concept, last_seen_ts AS timestamp, predicted_recall AS memory_score "
            "FROM memory_decay ORDER BY last_seen_ts ASC",
            conn
        )
        print("\nTest fetch_decay output:")
        print(df_test.head())

    finally:
        conn.close()

if __name__ == "__main__":
    test_memory_decay()
