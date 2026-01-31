# dashboard/new_dashboard_part1.py
import sys, os, sqlite3
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import streamlit as st

# Add project root
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Streamlit Page Config
# -----------------------------
st.set_page_config(
    page_title="FKT Tracker Dashboard", layout="wide"
)
st.markdown("""
<style>
body {background-color: #0e1117; color: #e6eef3;}
h1, h2, h3, h4, h5 {color:#8be9fd;}
.stButton>button {background-color:#282c34;color:#cdeacb;border-radius:6px;}
.stDataFrame th {background-color:#181c22;color:#8be9fd;}
.stDataFrame td {background-color:#0e1117;color:#cdeacb;}
</style>
""", unsafe_allow_html=True)
st.title("🔮 Forgotten Knowledge Tracker — Next-Gen Dashboard")

# -----------------------------
# DB Loading with caching
# -----------------------------
@st.cache_data(ttl=300)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Sessions
        df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
        df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors="coerce")
        df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors="coerce")
        df_sessions["duration_min"] = ((df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds()/60).clip(lower=0)
        df_sessions["app_name"].fillna("Unknown App", inplace=True)
        df_sessions["intent_label"].fillna("N/A", inplace=True)
        df_sessions["audio_label"].fillna("N/A", inplace=True)

        # Memory decay
        df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
        for col in ["last_seen_ts","updated_at"]:
            if col in df_decay.columns:
                df_decay[col] = pd.to_datetime(df_decay[col], errors="coerce")

        # Metrics
        df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
        if "next_review_time" in df_metrics.columns:
            df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors="coerce")

        # Multi-modal logs
        df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
        if "timestamp" in df_logs.columns:
            df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors="coerce")

        return df_sessions, df_decay, df_metrics, df_logs
    finally:
        conn.close()

df_sessions, df_decay, df_metrics, df_logs = load_data()

# -----------------------------
# Sync Knowledge Graph
# -----------------------------
try:
    sync_db_to_graph()
    G = get_graph()
except Exception:
    G = None

st.success("✅ Data Loaded and Knowledge Graph Synced")
# -----------------------------
# Sidebar Filters & Controls
# -----------------------------
st.sidebar.header("Tracker Controls")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)
st.sidebar.markdown("---")

st.sidebar.subheader("Graph Visual Settings")
node_min_size = st.sidebar.slider("Min Node Size", 50, 800, 120)
node_max_size = st.sidebar.slider("Max Node Size", 200, 3000, 700)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.05, 1.0, 0.45)

st.sidebar.subheader("Data Filters")
date_range = st.sidebar.date_input(
    "Filter Sessions by Date Range",
    [datetime.now() - timedelta(days=30), datetime.now()]
)
selected_apps = st.sidebar.multiselect(
    "Filter Apps", options=df_sessions["app_name"].unique(), default=list(df_sessions["app_name"].unique())
)

# -----------------------------
# Apply Filters
# -----------------------------
df_sessions_filtered = df_sessions[
    (df_sessions["start_ts"].dt.date >= date_range[0]) &
    (df_sessions["start_ts"].dt.date <= date_range[1]) &
    (df_sessions["app_name"].isin(selected_apps))
] if not df_sessions.empty else pd.DataFrame()

# -----------------------------
# KPI Cards
# -----------------------------
def card_html(title, value, subtitle=""):
    return f"""
    <div style="
        background: linear-gradient(160deg, rgba(22,27,34,0.85), rgba(10,12,16,0.6));
        border-radius: 12px;
        padding: 14px;
        margin:6px;
        text-align:center;
        box-shadow: 0 6px 22px rgba(0,0,0,0.5);">
        <h4 style="color:#8be9fd;margin:0;">{title}</h4>
        <p style="color:#cdeacb;margin:0;font-size:18px;font-weight:600;">{value}</p>
        <div style="color:#8da3b3;font-size:12px;">{subtitle}</div>
    </div>
    """

total_hours = df_sessions_filtered["duration_min"].sum()/60 if not df_sessions_filtered.empty else 0
avg_session = df_sessions_filtered["duration_min"].mean() if not df_sessions_filtered.empty else 0
num_sessions = len(df_sessions_filtered)
unique_concepts = len(G.nodes) if G else 0
avg_mem_score = round(np.mean([G.nodes[n].get("memory_score",0.3) for n in G.nodes]),2) if G else 0
upcoming_reminders = len(df_metrics[df_metrics["next_review_time"]>datetime.now()]) if not df_metrics.empty else 0

cols = st.columns(6)
cols[0].markdown(card
