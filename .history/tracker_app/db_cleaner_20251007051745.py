# db_cleaner.py
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
from config import DB_PATH

def clean_sessions(conn: sqlite3.Connection) -> int:
    """Clean sessions table: fix missing timestamps and remove invalid rows."""
    df = pd.read_sql("SELECT * FROM sessions", conn)

    # Track rows removed
    removed_rows = 0

    # Drop rows where both timestamps are missing
    mask_both_missing = df['start_ts'].isna() & df['end_ts'].isna()
    removed_rows += mask_both_missing.sum()
    df = df[~mask_both_missing]

    # Fix rows with only start_ts missing
    mask_start_missing = df['start_ts'].isna() & df['end_ts'].notna()
    df.loc[mask_start_missing, 'start_ts'] = pd.to_datetime(df.loc[mask_start_missing, 'end_ts']) - timedelta(seconds=5)

    # Fix rows with only end_ts missing
    mask_end_missing = df['end_ts'].isna() & df['start_ts'].notna()
    df.loc[mask_end_missing, 'end_ts'] = pd.to_datetime(df.loc[mask_end_missing, 'start_ts']) + timedelta(seconds=5)

    # Ensure timestamps are datetime objects
    df['start_ts'] = pd.to_datetime(df['start_ts'])
    df['end_ts'] = pd.to_datetime(df['end_ts'])

    # Write cleaned data back to DB
    df.to_sql('sessions', conn, if_exists='replace', index=False)
    return removed_rows

def clean_multi_modal_logs(conn: sqlite3.Connection) -> int:
    """Remove multi-modal logs with invalid session references."""
    df_multi = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    df_sessions = pd.read_sql("SELECT id FROM sessions", conn)

    if 'session_id' not in df_multi.columns:
        print("[WARNING] multi_modal_logs missing session_id column.")
        return 0

    invalid_mask = ~df_multi['session_id'].isin(df_sessions['id'])
    removed_rows = invalid_mask.sum()
    df_multi = df_multi[~invalid_mask]

    df_multi.to_sql('multi_modal_logs', conn, if_exists='replace', index=False)
    return removed_rows

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        removed_sessions = clean_sessions(conn)
        removed_multi = clean_multi_modal_logs(conn)

        print("✅ Database cleaning completed.")
        print(f"Removed {removed_sessions} invalid rows from sessions.")
        print(f"Removed {removed_multi} invalid rows from multi_modal_logs.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
