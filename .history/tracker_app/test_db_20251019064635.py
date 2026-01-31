import sqlite3
import pandas as pd
from config import DB_PATH

def test_sessions_datetime_format(limit=50):
    """
    Check the sessions table for valid and invalid timestamp formats.
    
    Args:
        limit (int): Number of rows to test (default 50)
    """
    conn = sqlite3.connect(DB_PATH)
    query = f"SELECT id, start_ts, end_ts, app_name, window_title FROM sessions LIMIT {limit}"
    df = pd.read_sql(query, conn)
    conn.close()

    # Try to convert timestamps to datetime
    df["start_dt"] = pd.to_datetime(df["start_ts"], errors="coerce")
    df["end_dt"] = pd.to_datetime(df["end_ts"], errors="coerce")

    # Duration in minutes
    df["duration_min"] = (df["end_dt"] - df["start_dt"]).dt.total_seconds() / 60

    # Valid rows: both timestamps are valid and duration > 0
    df_valid = df.dropna(subset=["start_dt", "end_dt"])
    df_valid = df_valid[df_valid["duration_min"] > 0]

    # Invalid rows
    df_invalid = df[~df.index.isin(df_valid.index)]

    print(f"\n=== Valid Sessions ({len(df_valid)}) ===")
    print(df_valid[["id", "start_ts", "end_ts", "duration_min", "app_name", "window_title"]])

    print(f"\n=== Invalid Sessions ({len(df_invalid)}) ===")
    print(df_invalid[["id", "start_ts", "end_ts", "app_name", "window_title"]])

if __name__ == "__main__":
    test_sessions_datetime_format(limit=100)
