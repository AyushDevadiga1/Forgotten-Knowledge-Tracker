# test_db_checkup.py
import sqlite3
import pandas as pd
from config import DB_PATH
from datetime import datetime

def check_tables(conn):
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
    print("Tables:", tables['name'].tolist())
    return tables['name'].tolist()

def check_columns(conn, table_name):
    cols = pd.read_sql(f"PRAGMA table_info({table_name})", conn)
    print(f"{table_name} columns:", [c for c in cols['name']])
    return cols

def check_sessions(conn):
    df = pd.read_sql("SELECT * FROM sessions", conn, parse_dates=["start_ts", "end_ts"])
    anomalies = []
    if df.empty:
        print("⚠️ sessions table is empty")
    else:
        # Check for nulls
        nulls = df.isnull().sum()
        if nulls.any():
            print("⚠️ Nulls in sessions:\n", nulls[nulls > 0])
            anomalies.append("nulls")
        # Check end_ts >= start_ts
        invalid_times = df[df["end_ts"] < df["start_ts"]]
        if not invalid_times.empty:
            print("⚠️ Sessions with end_ts < start_ts:\n", invalid_times)
            anomalies.append("time")
        # Check negative interaction_rate
        neg_interaction = df[df["interaction_rate"] < 0]
        if not neg_interaction.empty:
            print("⚠️ Negative interaction_rate:\n", neg_interaction)
            anomalies.append("interaction")
    print(f"sessions table check complete. Anomalies: {anomalies}\n")
    return anomalies

def check_multi_modal_logs(conn):
    df = pd.read_sql("SELECT * FROM multi_modal_logs", conn, parse_dates=["timestamp"])
    anomalies = []
    if df.empty:
        print("⚠️ multi_modal_logs table is empty")
    else:
        # Nulls
        nulls = df.isnull().sum()
        if nulls.any():
            print("⚠️ Nulls in multi_modal_logs:\n", nulls[nulls > 0])
            anomalies.append("nulls")
        # Memory score bounds
        out_of_bounds = df[(df["memory_score"] < 0) | (df["memory_score"] > 1)]
        if not out_of_bounds.empty:
            print("⚠️ memory_score out of bounds [0,1]:\n", out_of_bounds)
            anomalies.append("memory_score")
    print(f"multi_modal_logs table check complete. Anomalies: {anomalies}\n")
    return anomalies

def check_memory_decay(conn):
    df = pd.read_sql("SELECT * FROM memory_decay", conn, parse_dates=["last_seen_ts","updated_at"])
    anomalies = []
    if df.empty:
        print("⚠️ memory_decay table is empty")
    else:
        # Nulls
        nulls = df.isnull().sum()
        if nulls.any():
            print("⚠️ Nulls in memory_decay:\n", nulls[nulls > 0])
            anomalies.append("nulls")
        # Memory bounds
        out_of_bounds = df[(df["predicted_recall"] < 0) | (df["predicted_recall"] > 1)]
        if not out_of_bounds.empty:
            print("⚠️ predicted_recall out of bounds [0,1]:\n", out_of_bounds)
            anomalies.append("predicted_recall")
    print(f"memory_decay table check complete. Anomalies: {anomalies}\n")
    return anomalies

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    tables = check_tables(conn)
    
    if "sessions" in tables:
        check_sessions(conn)
    if "multi_modal_logs" in tables:
        check_multi_modal_logs(conn)
    if "memory_decay" in tables:
        check_memory_decay(conn)
    
    conn.close()
    print("✅ DB checkup complete.")
