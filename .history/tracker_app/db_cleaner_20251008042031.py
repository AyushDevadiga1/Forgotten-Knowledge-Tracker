# clean_db.py
import sqlite3
import pandas as pd
from config import DB_PATH
import logging

logging.basicConfig(
    filename="logs/clean_db.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def clean_sessions(conn):
    df = pd.read_sql("SELECT * FROM sessions", conn)
    total_rows = len(df)
    logging.info(f"Sessions before cleaning: {total_rows}")

    # Drop rows with null audio/intent/confidence
    df_clean = df.dropna(subset=["audio_label", "intent_label", "intent_confidence"])
    dropped = total_rows - len(df_clean)
    logging.info(f"Dropped {dropped} rows from sessions due to nulls")

    # Optional: validate duration
    df_clean["start_ts"] = pd.to_datetime(df_clean["start_ts"], errors='coerce')
    df_clean["end_ts"] = pd.to_datetime(df_clean["end_ts"], errors='coerce')
    df_clean = df_clean[df_clean["end_ts"] > df_clean["start_ts"]]

    # Replace table
    df_clean.to_sql("sessions", conn, if_exists="replace", index=False)
    logging.info(f"Sessions cleaned. Remaining rows: {len(df_clean)}")

def clean_multi_modal_logs(conn):
    df = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    logging.info(f"multi_modal_logs rows before cleaning: {len(df)}")

    # Drop rows with null timestamp
    df_clean = df.dropna(subset=["timestamp"])
    df_clean.to_sql("multi_modal_logs", conn, if_exists="replace", index=False)
    logging.info(f"multi_modal_logs cleaned. Remaining rows: {len(df_clean)}")

def clean_memory_decay(conn):
    df = pd.read_sql("SELECT * FROM memory_decay", conn)
    logging.info(f"memory_decay rows before cleaning: {len(df)}")

    # Drop rows with null predicted_recall or keyword/concept
    drop_cols = [col for col in ["concept", "last_seen_ts", "predicted_recall"] if col in df.columns]
    df_clean = df.dropna(subset=drop_cols)
    df_clean.to_sql("memory_decay", conn, if_exists="replace", index=False)
    logging.info(f"memory_decay cleaned. Remaining rows: {len(df_clean)}")

def clean_metrics(conn):
    df = pd.read_sql("SELECT * FROM metrics", conn)
    logging.info(f"metrics rows before cleaning: {len(df)}")

    # Drop rows with null concept or next_review_time
    drop_cols = [col for col in ["concept", "next_review_time", "memory_score"] if col in df.columns]
    df_clean = df.dropna(subset=drop_cols)
    df_clean.to_sql("metrics", conn, if_exists="replace", index=False)
    logging.info(f"metrics cleaned. Remaining rows: {len(df_clean)}")

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        clean_sessions(conn)
        clean_multi_modal_logs(conn)
        clean_memory_decay(conn)
        clean_metrics(conn)
        logging.info("✅ Database cleaning complete.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
