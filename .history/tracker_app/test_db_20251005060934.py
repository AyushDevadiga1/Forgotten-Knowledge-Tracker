import sqlite3
import pandas as pd
import os

DB_PATH = r"C:\Users\hp\Desktop\FKT\tracker_app\tracker.db"  # Update your DB path
REPORT_DIR = r"C:\Users\hp\Desktop\FKT\tracker_app\db_reports"  # Folder to save CSVs

# Create report folder if not exists
os.makedirs(REPORT_DIR, exist_ok=True)

# Define expected schema: table -> column -> expected type
EXPECTED_SCHEMA = {
    "sessions": {
        "start_ts": "datetime",
        "end_ts": "datetime",
        "app_name": "str",
        "audio_label": "str",
        "intent_label": "str",
        "intent_confidence": "numeric"
    },
    "multi_modal_logs": {
        "timestamp": "datetime"
    },
    "memory_decay": {
        "last_seen_ts": "datetime",
        "updated_at": "datetime",
        "predicted_recall": "numeric"
    },
    "metrics": {
        "concept": "str",
        "next_review_time": "datetime",
        "memory_score": "numeric"
    }
}

def check_table_validity(conn, table_name, schema):
    invalid_rows = pd.DataFrame()
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    
    for col, col_type in schema.items():
        if col not in df.columns:
            continue
        if col_type == "datetime":
            invalid_mask = pd.to_datetime(df[col], errors='coerce').isna()
        elif col_type == "numeric":
            invalid_mask = pd.to_numeric(df[col], errors='coerce').isna()
        elif col_type == "str":
            invalid_mask = df[col].isna() | (df[col].apply(lambda x: not isinstance(x, str)))
        else:
            continue

        if invalid_mask.any():
            invalid_rows = pd.concat([invalid_rows, df[invalid_mask]])
    
    # Additional logical checks
    if table_name == "sessions" and "start_ts" in df.columns and "end_ts" in df.columns:
        invalid_time_mask = pd.to_datetime(df["end_ts"], errors='coerce') <= pd.to_datetime(df["start_ts"], errors='coerce')
        if invalid_time_mask.any():
            invalid_rows = pd.concat([invalid_rows, df[invalid_time_mask]])

    invalid_rows = invalid_rows.drop_duplicates()
    return invalid_rows

def check_database_and_export(db_path, report_dir):
    conn = sqlite3.connect(db_path)
    all_invalid = {}

    for table, schema in EXPECTED_SCHEMA.items():
        invalid_rows = check_table_validity(conn, table, schema)
        if not invalid_rows.empty:
            all_invalid[table] = invalid_rows
            # Export CSV
            csv_path = os.path.join(report_dir, f"{table}_invalid_rows.csv")
            invalid_rows.to_csv(csv_path, index=False)
            print(f"❌ Invalid rows in '{table}' exported to {csv_path}")
    
    conn.close()

    if not all_invalid:
        print("✅ All tables are valid.")
    else:
        print(f"\nSummary: {len(all_invalid)} table(s) contain invalid rows. Check CSVs in {report_dir}")
    return all_invalid

if __name__ == "__main__":
    invalid_data = check_database_and_export(DB_PATH, REPORT_DIR)
