import sqlite3
import pandas as pd
from datetime import datetime, timedelta

from config import DB

conn = sqlite3.connect(DB_PATH)

# -------------------------------
# 1. Clean sessions table
# -------------------------------
df_sessions = pd.read_sql("SELECT * FROM sessions", conn)

# Fix missing timestamps
df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors="coerce")
df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors="coerce")
df_sessions["end_ts"] = df_sessions["end_ts"].where(
    df_sessions["end_ts"] > df_sessions["start_ts"],
    df_sessions["start_ts"] + timedelta(seconds=5)
)

# Fill missing app_name
df_sessions["app_name"] = df_sessions["app_name"].fillna("Unknown App")

# Write back cleaned table
df_sessions.to_sql("sessions", conn, if_exists="replace", index=False)

# -------------------------------
# 2. Clean multi_modal_logs table
# -------------------------------
df_multi = pd.read_sql("SELECT * FROM multi_modal_logs", conn)

# Ensure session_id exists
if "session_id" not in df_multi.columns:
    df_multi["session_id"] = None

# Remove invalid session references
valid_sessions = set(df_sessions["id"])
df_multi = df_multi[df_multi["session_id"].isin(valid_sessions) | df_multi["session_id"].isna()]

df_multi.to_sql("multi_modal_logs", conn, if_exists="replace", index=False)

# -------------------------------
# 3. Clean memory_decay table
# -------------------------------
df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)

# Ensure concept column exists
if "concept" not in df_decay.columns:
    df_decay.rename(columns={"keyword": "concept"}, inplace=True)

# Fill missing concept
df_decay["concept"] = df_decay["concept"].fillna("Unknown Concept")

df_decay.to_sql("memory_decay", conn, if_exists="replace", index=False)

conn.close()
print("✅ Database cleaned manually")
