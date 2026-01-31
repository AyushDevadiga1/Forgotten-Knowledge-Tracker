# db_full_integrity_check
import sqlite3
import pandas as pd
from datetime import timedelta
from config import DB_PATH
  # Update with your DB path

def check_sessions(df_sessions):
    errors = []

    # Ensure timestamps are datetime
    df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors="coerce")
    df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors="coerce")

    # Missing timestamps
    missing_start = df_sessions["start_ts"].isna().sum()
    missing_end = df_sessions["end_ts"].isna().sum()
    if missing_start:
        errors.append(f"Missing start_ts: {missing_start} rows")
    if missing_end:
        errors.append(f"Missing end_ts: {missing_end} rows")

    # Zero or negative durations
    df_sessions["end_ts"] = df_sessions["end_ts"].where(
        df_sessions["end_ts"] > df_sessions["start_ts"],
        df_sessions["start_ts"] + pd.Timedelta(seconds=5)
    )
    df_sessions["duration_min"] = (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60
    zero_dur = (df_sessions["duration_min"] <= 0).sum()
    if zero_dur:
        errors.append(f"Zero or negative session durations: {zero_dur} rows")

    # App name checks
    missing_app = df_sessions["app_name"].isna().sum()
    if missing_app:
        errors.append(f"Missing app_name: {missing_app} rows")

    # ID uniqueness
    duplicate_ids = df_sessions["id"].duplicated().sum()
    if duplicate_ids:
        errors.append(f"Duplicate session IDs: {duplicate_ids} rows")

    return errors, df_sessions

import pandas as pd

def check_multi_modal(df_multi: pd.DataFrame, df_sessions: pd.DataFrame) -> dict:
    """
    Checks integrity of the multi_modal_logs table.

    Args:
        df_multi: DataFrame of multi-modal logs.
        df_sessions: DataFrame of sessions table.

    Returns:
        dict: A summary report of errors and issues.
    """
    report = {
        "missing_session_id_column": False,
        "invalid_session_references": 0,
        "total_rows": len(df_multi)
    }

    # Check if session_id column exists
    if "session_id" not in df_multi.columns:
        report["missing_session_id_column"] = True
        report["message"] = "Column 'session_id' is missing in multi_modal_logs"
        return report

    # Check for session_id values not present in sessions table
    invalid_session_count = (~df_multi["session_id"].isin(df_sessions["id"])).sum()
    report["invalid_session_references"] = int(invalid_session_count)

    if invalid_session_count > 0:
        report["message"] = f"{invalid_session_count} rows have invalid session references"
    else:
        report["message"] = "All session references are valid"

    return report


import pandas as pd

def check_memory_decay(df_decay: pd.DataFrame) -> dict:
    """
    Checks integrity of the memory_decay table.

    Args:
        df_decay: DataFrame of memory decay logs.

    Returns:
        dict: A summary report of errors and issues.
    """
    report = {
        "missing_concept_column": False,
        "missing_concept_count": 0,
        "total_rows": len(df_decay)
    }

    # Check if concept column exists
    if "concept" not in df_decay.columns:
        report["missing_concept_column"] = True
        report["message"] = "Column 'concept' is missing in memory_decay"
        return report

    # Count missing concept values
    missing_concept_count = df_decay["concept"].isna().sum()
    report["missing_concept_count"] = int(missing_concept_count)

    if missing_concept_count > 0:
        report["message"] = f"{missing_concept_count} rows have missing concept values"
    else:
        report["message"] = "All concepts are valid"

    return report


def check_metrics(df_metrics):
    errors = []
    nan_counts = df_metrics.isna().sum().sum()
    if nan_counts:
        errors.append(f"NaN values in metrics table: {nan_counts}")
    return errors

def main():
    conn = sqlite3.connect(DB_PATH)

    report = {}

    # Sessions
    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    errors, df_sessions_fixed = check_sessions(df_sessions)
    report["sessions"] = errors

    # Multi-modal logs
    df_multi = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    report["multi_modal_logs"] = check_multi_modal(df_multi, df_sessions_fixed)

    # Memory decay
    df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
    report["memory_decay"] = check_memory_decay(df_decay)

    # Metrics
    df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
    report["metrics"] = check_metrics(df_metrics)

    # Print full report
    print("\n=== DATABASE INTEGRITY REPORT ===")
    for table, errs in report.items():
        print(f"\nTable: {table}")
        if errs:
            for e in errs:
                print(f"  - {e}")
        else:
            print("  No issues found ✅")

    conn.close()

if __name__ == "__main__":
    main()
