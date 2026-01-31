# dashboard/fkt_dashboard.py
"""
FKT Dashboard — Fixed & Hardened Streamlit App with Tab Slider
- Sidebar slider to switch tabs (all tabs accessible)
- Defensive parsing for DB tables
- Robust date filtering
- Safer 3D KG rendering with keyword hover
- Fixed memory decay plotting and predicted forgetting guards
- Improved OCR parsing fallbacks
- Better System Health checks and error handling
"""

import sys
import os
import sqlite3
import json
import re
from datetime import datetime, timedelta, date
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------- Project Root & Paths -----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import DB_PATH
try:
    from core.knowledge_graph import get_graph, sync_db_to_graph
except Exception:
    get_graph = None
    sync_db_to_graph = None

# ----------------------------- Streamlit Page Setup & Theme -----------------------------
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide")
st.markdown("""
<style>
body { background-color: #0b0f14; color: #e6eef3; }
.stApp { background: linear-gradient(180deg,#071014,#0b0f14); }
.metric-card { background: linear-gradient(160deg, rgba(22,27,34,0.85), rgba(10,12,16,0.6)); border-radius: 14px; padding: 14px; margin: 6px 6px; box-shadow: 0 6px 22px rgba(0,0,0,0.5); text-align: center; }
.metric-card h4 { color: #8be9fd; margin:0 0 6px 0; }
.metric-card p { color: #cdeacb; margin:0; font-size:18px; font-weight:600; }
.small-muted { color: #8da3b3; font-size:12px; }
</style>
""", unsafe_allow_html=True)

st.title("🔮 Forgotten Knowledge Tracker — Visual Intelligence Dashboard")
st.markdown("A visually-rich, interactive dashboard for sessions, memory scores, knowledge graph, and system health.")

# ----------------------------- Sidebar Controls -----------------------------
st.sidebar.title("Tracker Controls")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)
st.sidebar.markdown("---")

st.sidebar.subheader("Graph Visual Settings")
node_min_size = st.sidebar.slider("Min Node Size", 10, 800, 120)
node_max_size = st.sidebar.slider("Max Node Size", 50, 3000, 700)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.05, 1.0, 0.45)

st.sidebar.subheader("Data Filters")
date_range = st.sidebar.date_input(
    "Filter Sessions by Date Range",
    value=[(datetime.now() - timedelta(days=30)).date(), datetime.now().date()]
)

# ----------------------------- Tab Selection Slider -----------------------------
tab_names = [
    "Overview", "Knowledge Graph (3D)", "Sessions",
    "Memory Decay", "Predicted Forgetting",
    "Multi-Modal Logs", "Upcoming Reminders",
    "OCR Insights", "Audio / Intent Analysis",
    "Visual Attention Stats", "Performance Insights", "System Health"
]
tab_index = st.sidebar.slider("Select Tab", 0, len(tab_names)-1, 0, format="%d: " + tab_names[0])
selected_tab = tab_names[tab_index]

# ----------------------------- Utilities / DB helpers -----------------------------
@st.cache_data(ttl=300)
def load_cleaned_data():
    conn = sqlite3.connect(DB_PATH)
    try:
        try: df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
        except Exception: df_sessions = pd.DataFrame()
        if not df_sessions.empty:
            for col in ["start_ts", "end_ts"]:
                if col in df_sessions.columns:
                    df_sessions[col] = pd.to_datetime(df_sessions[col], errors="coerce")
            df_sessions.fillna({"app_name":"Unknown App", "audio_label":"N/A", "intent_label":"N/A", "intent_confidence":0}, inplace=True)
            if "start_ts" in df_sessions.columns and "end_ts" in df_sessions.columns:
                df_sessions["duration_min"] = ((df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds()/60).clip(lower=0)
            else: df_sessions["duration_min"] = 0.0
        else:
            df_sessions = pd.DataFrame(columns=["start_ts", "end_ts", "app_name", "duration_min"])
        try: df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
        except Exception: df_logs = pd.DataFrame()
        if not df_logs.empty and "timestamp" in df_logs.columns:
            df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors="coerce")
        try: df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
        except Exception: df_decay = pd.DataFrame()
        if not df_decay.empty:
            if "concept" in df_decay.columns: df_decay["concept"] = df_decay["concept"].astype(str)
            for col in ["last_seen_ts", "updated_at"]:
                if col in df_decay.columns: df_decay[col] = pd.to_datetime(df_decay[col], errors="coerce")
            if "predicted_recall" in df_decay.columns:
                df_decay["predicted_recall"] = pd.to_numeric(df_decay["predicted_recall"], errors="coerce").fillna(0).clip(0,1)
        try: df_metrics = pd.read_sql("SELECT concept, next_review_time, memory_score FROM metrics", conn)
        except Exception: df_metrics = pd.DataFrame(columns=["concept", "next_review_time", "memory_score"])
        if not df_metrics.empty:
            df_metrics["concept"] = df_metrics["concept"].astype(str)
            if "next_review_time" in df_metrics.columns: df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors="coerce")
        return df_sessions, df_logs, df_decay, df_metrics
    finally:
        conn.close()

def parse_ocr_keywords_field(val):
    if val is None: return {}
    if isinstance(val, dict): return val
    if isinstance(val, (list, tuple)): return {str(x):{"score":0.5} for x in val}
    if not isinstance(val,str):
        try: val = str(val)
        except Exception: return {}
    val = val.strip()
    if val == "": return {}
    try:
        parsed = json.loads(val)
        if isinstance(parsed, dict): return parsed
        if isinstance(parsed, list): return {str(k):{"score":0.5} for k in parsed}
    except Exception: pass
    try:
        parsed = json.loads(val.replace("'","\""))
        if isinstance(parsed, dict): return parsed
        if isinstance(parsed, list): return {str(k):{"score":0.5} for k in parsed}
    except Exception: pass
    parts = [p.strip() for p in re.split(r"[,
;]+", val) if p.strip()]
    return {k:{"score":0.5} for k in parts}

# ----------------------------- Load Data -----------------------------
df_sessions, df_logs, df_decay, df_metrics = load_cleaned_data()

# Apply date filter to sessions
df_sessions = df_sessions.copy()
if isinstance(date_range, (list, tuple)) and len(date_range)>=2:
    start_date, end_date = date_range[0], date_range[1]
else: start_date = end_date = date_range
if isinstance(start_date, datetime): start_date = start_date.date()
if isinstance(end_date, datetime): end_date = end_date.date()
if not df_sessions.empty and "start_ts" in df_sessions.columns:
    try: df_sessions = df_sessions[(df_sessions["start_ts"].dt.date>=start_date) & (df_sessions["start_ts"].dt.date<=end_date)]
    except Exception:
        df_sessions["start_ts"] = pd.to_datetime(df_sessions.get("start_ts"), errors="coerce")
        df_sessions = df_sessions[(df_sessions["start_ts"].dt.date>=start_date) & (df_sessions["start_ts"].dt.date<=end_date)]

# Sync KG
G = nx.Graph()
if sync_db_to_graph is not None and get_graph is not None:
    try: sync_db_to_graph(); G = get_graph() or nx.Graph()
    except Exception: G = nx.Graph()
else:
    try:
        kg_path = os.path.join(PROJECT_ROOT, "data", "kg_graph.gpickle")
        if os.path.exists(kg_path): G = nx.read_gpickle(kg_path)
    except Exception: G = nx.Graph()
concepts = list(G.nodes)
