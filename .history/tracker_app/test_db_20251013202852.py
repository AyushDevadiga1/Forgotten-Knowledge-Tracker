import sqlite3
import pandas as pd
from config import DB_PATH
from datetime import datetime

# -----------------------------
# Validation helpers
# -----------------------------
def is_valid_datetime(value):
    try:
        if pd.isna(value):
            return False
        datetime.fromisoformat(value)
        return True
    except:
        return False

def check_sessions(df):
    mask = df["start_ts"].apply(is_valid_datetime) & \
           df["end_ts"].apply(is_valid_datetime) & \
           df["interaction_rate"].apply(lambda x: pd.isna(x) or isinstance(x, (int,float))) & \
           df["interaction_count"].apply(lambda x: pd.isna(x) or isinstance(x, (int,float))) & \
           df["intent_confidence"].apply(lambda x: pd.isna(x) or isinstance(x, (int,float)))
    mask &= df.apply(lambda row: datetime.fromisoformat(row["end_ts"]) >= datetime.fromisoformat(row["start_ts"]) if is_valid_datetime(row["start_ts"]) and is_valid_datetime(row["end_ts"]) else False, axis=1)
    return mask

def check_multi_modal_logs(df):
    mask = df["timestamp"].apply(is_valid_datetime) & \
           df["attention_score"].apply(lambda x: pd.isna(x) or isinstance(x, (int,float))) & \
           df["interaction_rate"].apply(lambda x: pd.isna(x) or isinstance(x, (int,float))) & \
           df["intent_confidence"].apply(lambda x: pd.isna(x) or isinstance(x, (int,float))) & \
           df["memory_score"].apply(lambda x: pd.isna(x) or isinstance(x, (int,float)))
    return mask

def check_memory_decay(df):
    mask = df["last_seen_ts"].apply(is_valid_datetime) & \
           df["predicted_recall"].apply(lambda x: pd.isna(x) or isinstance(x, (int,float))) & \
           df["observed_usage"].apply(lambda x: pd.isna(x) or isinstance(x, (int,float))) & \
           df["updated_at"].apply(lambda x: is_valid_datetime(x) or pd.isna(x))
    return mask

def check_metrics(df):
    mask = df["next_review_time"].apply(lambda x: is_valid_datetime(x)) & \
           df["memory_score"].apply(lambda x: pd.isna(x) or isinstance(x, (int,float)))
    return mask

# -----------------------------
# Safe table check function
# -----------------------------
def check_table(conn, table_name, check_func):
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    mask = check_func(df)
    invalid_rows = df[~mask]

    if not invalid_rows.empty:
        invalid_rows.to_csv(f"{table_name}_invalid_rows.csv", index=False)
        print(f"❌ Invalid rows in '{table_name}' exported to {table_name}_invalid_rows.csv")
    else:
        print(f"✅ No invalid rows found in '{table_name}'")

    return len(df), mask.sum(), len(df) - mask.sum()

# -----------------------------
# Run full DB check (safe mode)
# -----------------------------
def check_db_safe():
    conn = sqlite3.connect(DB_PATH)
    summary = []

    tables_checks = {
        "sessions": check_sessions,
        "multi_modal_logs": check_multi_modal_logs,
        "memory_decay": check_memory_decay,
        "metrics": check_metrics
    }

    for table, check_func in tables_checks.items():
        total, valid, invalid = check_table(conn, table, check_func)
        summary.append({"Table": table, "Total Rows": total, "Valid Rows": valid, "Invalid Rows": invalid})

    conn.close()
    summary_df = pd.DataFrame(summary)
    print("\n📊 Database Summary (Safe Check):")
    print(summary_df.to_string(index=False))

if __name__ == "__main__":
    check_db_safe()
