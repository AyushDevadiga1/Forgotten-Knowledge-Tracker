# db_full_integrity_check
import sqlite3
import pandas as pd
from datetime import timedelta
from co  # Update with your DB path

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

def check_multi_modal(df_multi, df_sessions):
    errors = []

    # Missing timestamps
    df_multi["timestamp"] = pd.to_datetime(df_multi["timestamp"], errors="coerce")
    missing_ts = df_multi["timestamp"].isna().sum()
    if missing_ts:
        errors.append(f"Missing timestamps: {missing_ts} rows")

    # Check session_id exists
    invalid_session = (~df_multi["session_id"].isin(df_sessions["id"])).sum()
    if invalid_session:
        errors.append(f"Invalid session_id references: {invalid_session} rows")

    # Missing labels
    required_cols = ["audio_label", "intent_label"]
    for col in required_cols:
        missing = df_multi[col].isna().sum()
        if missing:
            errors.append(f"Missing {col}: {missing} rows")

    return errors

def check_memory_decay(df_decay):
    errors = []

    # Missing concept
    missing_concept = df_decay["concept"].isna().sum()
    if missing_concept:
        errors.append(f"Missing concept: {missing_concept} rows")

    # Decay score validity
    invalid_decay = df_decay[(df_decay["decay_score"] < 0) | (df_decay["decay_score"] > 1)].shape[0]
    if invalid_decay:
        errors.append(f"Invalid decay_score values: {invalid_decay} rows")

    return errors

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
