# dashboard/dashboard_pro.py
import sys
import os
import sqlite3
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Project Root & Modules
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)
from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Load and Clean Data
# -----------------------------
@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)

    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors='coerce')
    df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors='coerce')
    df_sessions["app_name"] = df_sessions["app_name"].fillna("Unknown App")
    df_sessions["audio_label"] = df_sessions["audio_label"].fillna("N/A")
    df_sessions["intent_label"] = df_sessions["intent_label"].fillna("N/A")
    df_sessions["intent_confidence"] = pd.to_numeric(df_sessions["intent_confidence"], errors='coerce').fillna(0)
    df_sessions["duration_min"] = (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60

    df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors='coerce')

    df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
    df_decay["last_seen_ts"] = pd.to_datetime(df_decay["last_seen_ts"], errors='coerce')
    df_decay["updated_at"] = pd.to_datetime(df_decay["updated_at"], errors='coerce')

    df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
    df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors='coerce')

    conn.close()
    return df_sessions, df_logs, df_decay, df_metrics

df_sessions, df_logs, df_decay, df_metrics = load_data()
df_sessions_filtered = df_sessions.dropna(subset=["start_ts", "end_ts"]) if not df_sessions.empty else pd.DataFrame()

# -----------------------------
# Streamlit Page Setup
# -----------------------------
st.set_page_config(page_title="🔮 Forgotten Knowledge Tracker", layout="wide")
st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Visualize your learning sessions, memory scores, knowledge graph, upcoming reminders, and more.")

# -----------------------------
# Sidebar Settings
# -----------------------------
st.sidebar.title("Tracker Settings")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)
st.sidebar.markdown("---")
st.sidebar.subheader("Graph Visual Settings")
node_min_size = st.sidebar.slider("Min Node Size", 100, 500, 200)
node_max_size = st.sidebar.slider("Max Node Size", 500, 2000, 800)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.1, 1.0, 0.5)

# Sidebar Tab Navigation
tab_options = ["Overview", "Knowledge Graph", "3D Graph", "Sessions",
               "Memory Decay", "Predicted Forgetting", "Multi-Modal Logs", "Upcoming Reminders"]
selected_tab = st.sidebar.select_slider("Navigate Tabs", options=tab_options)

# -----------------------------
# Part 1: Overview Tab with Modern KPIs
# -----------------------------
if selected_tab == "Overview":
    st.subheader("📊 Dashboard Overview")

    # Metrics
    total_hours = df_sessions_filtered["duration_min"].sum() / 60 if not df_sessions_filtered.empty else 0
    avg_session = df_sessions_filtered["duration_min"].mean() if not df_sessions_filtered.empty else 0
    num_sessions = len(df_sessions_filtered)
    upcoming_reminders = len(df_metrics[df_metrics["next_review_time"] > datetime.now()])

    # Stylish KPI cards
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    kpi_col1.metric(label="Total Hours", value=f"{total_hours:.2f} h")
    kpi_col2.metric(label="Avg Session", value=f"{avg_session:.1f} min")
    kpi_col3.metric(label="Number of Sessions", value=f"{num_sessions}")
    kpi_col4.metric(label="Upcoming Reminders", value=f"{upcoming_reminders}")

    # Daily activity chart
    if not df_sessions_filtered.empty:
        daily_hours = df_sessions_filtered.groupby(df_sessions_filtered["start_ts"].dt.date)["duration_min"].sum() / 60
        fig_daily = px.bar(
            x=daily_hours.index,
            y=daily_hours.values,
            labels={"x":"Date", "y":"Hours"},
            title="Daily Learning Hours",
            color=daily_hours.values,
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_daily, use_container_width=True)
