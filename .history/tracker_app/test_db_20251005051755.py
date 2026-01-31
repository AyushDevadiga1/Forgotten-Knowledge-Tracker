import sqlite3
import pandas as pd
from datetime import datetime

# Path to your DB
from config impor db

# Connect to DB
conn = sqlite3.connect(DB_PATH)

# -----------------------------
# 1️⃣ Clean Sessions Table
# -----------------------------
df_sessions = pd.read_sql("SELECT * FROM sessions ORDER BY start_ts DESC", conn)

# Drop rows without timestamps
df_sessions = df_sessions.dropna(subset=["start_ts", "end_ts"])

# Fill missing app_name
df_sessions["app_name"] = df_sessions["app_name"].fillna("Unknown App")

# Convert timestamps to datetime
df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors='coerce')
df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors='coerce')

# Fix negative durations
df_sessions["end_ts"] = df_sessions["end_ts"].where(df_sessions["end_ts"] > df_sessions["start_ts"],
                                                   df_sessions["start_ts"] + pd.Timedelta(seconds=5))

# Compute duration in minutes
df_sessions["duration_min"] = (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60

# -----------------------------
# 2️⃣ Clean Multi-Modal Logs
# -----------------------------
df_logs = pd.read_sql("SELECT * FROM multi_modal_logs ORDER BY timestamp ASC", conn)

# Convert timestamp to datetime
df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors='coerce')

# Fill missing numeric values with 0
for col in ["attention_score", "interaction_rate", "memory_score", "intent_confidence"]:
    df_logs[col] = pd.to_numeric(df_logs[col], errors='coerce').fillna(0)

# Fill missing text columns
for col in ["window_title", "ocr_keywords", "audio_label", "intent_label"]:
    df_logs[col] = df_logs[col].fillna("N/A")

# -----------------------------
# 3️⃣ Clean Memory Decay Table
# -----------------------------
df_decay = pd.read_sql("SELECT * FROM memory_decay ORDER BY last_seen_ts ASC", conn)

# Convert timestamp to datetime
df_decay["last_seen_ts"] = pd.to_datetime(df_decay["last_seen_ts"], errors='coerce')
df_decay["updated_at"] = pd.to_datetime(df_decay["updated_at"], errors='coerce')

# Ensure numeric column is float
df_decay["predicted_recall"] = pd.to_numeric(df_decay["predicted_recall"], errors='coerce').fillna(0)

# -----------------------------
# Close DB connection
# -----------------------------
conn.close()

# -----------------------------
# Print summary
# -----------------------------
print("=== Sessions ===")
print(df_sessions.info())
print(df_sessions.head())

print("\n=== Multi-Modal Logs ===")
print(df_logs.info())
print(df_logs.head())

print("\n=== Memory Decay ===")
print(df_decay.info())
print(df_decay.head())
