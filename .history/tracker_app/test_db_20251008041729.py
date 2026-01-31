import sqlite3
import pandas as pd
from config import DB_PATH

TABLES = {
    "sessions": ["start_ts", "end_ts", "app_name", "window_title", "interaction_rate", "audio_label", "intent_label", "intent_confidence"],
    "multi_modal_logs": ["timestamp", "window_title", "ocr_keywords", "audio_label", "attention_score", "interaction_rate", "intent_label", "intent_confidence", "memory_score"],
    "memory_decay": ["keyword", "last_seen_ts", "predicted_recall", "observed_usage", "updated_at"],
    "metrics": ["concept", "next_review_time", "memory_score"]
}

conn = sqlite3.connect(DB_PATH)

for table, cols in TABLES.items():
    print(f"\nChecking table: {table}")
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    print(f"Total rows: {len(df)}")
    null_counts = df[cols].isnull().sum()
    print("Nulls per column:")
    print(null_counts[null_counts > 0])
    
    if table == "sessions":
        # check for negative durations or interaction rates
        if "start_ts" in df.columns and "end_ts" in df.columns:
            df["start_ts"] = pd.to_datetime(df["start_ts"], errors="coerce")
            df["end_ts"] = pd.to_datetime(df["end_ts"], errors="coerce")
            df["duration_sec"] = (df["end_ts"] - df["start_ts"]).dt.total_seconds()
            invalid_durations = df[df["duration_sec"] <= 0]
            print(f"Sessions with invalid duration: {len(invalid_durations)}")
    
    if table == "memory_decay":
        df["predicted_recall"] = pd.to_numeric(df["predicted_recall"], errors="coerce")
        invalid_recall = df[(df["predicted_recall"] < 0) | (df["predicted_recall"] > 1)]
        print(f"Rows with invalid predicted_recall: {len(invalid_recall)}")

conn.close()
