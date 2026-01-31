# ==========================================================
# dashboard_light.py | Lightweight FKT Dashboard
# ==========================================================

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import networkx as nx

# -----------------------------
# Project Root and Config
# -----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)
from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Streamlit Page Setup
# -----------------------------
st.set_page_config(page_title="⚡ FKT Dashboard (Lite)", layout="wide")
st.title("⚡ Forgotten Knowledge Tracker — Lightweight Dashboard")

# -----------------------------
# Load Data (Cached)
# -----------------------------
@st.cache_data(ttl=120)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
    df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
    conn.close()

    # clean sessions
    if not df_sessions.empty:
        df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors="coerce")
        df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors="coerce")
        df_sessions["duration_min"] = (
            (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60
        )
        df_sessions["app_name"] = df_sessions["app_name"].fillna("Unknown")

    if not df_decay.empty:
        df_decay["last_seen_ts"] = pd.to_datetime(df_decay["last_seen_ts"], errors="coerce")
        df_decay["updated_at"] = pd.to_datetime(df_decay["updated_at"], errors="coerce")

    if not df_metrics.empty:
        df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors="coerce")

    return df_sessions, df_decay, df_metrics


df_sessions, df_decay, df_metrics = load_data()
df_sessions_filtered = df_sessions.dropna(subset=["start_ts", "end_ts"]) if not df_sessions.empty else pd.DataFrame()

# -----------------------------
# Sidebar Filters
# -----------------------------
st.sidebar.header("Filters")
date_filter = st.sidebar.date_input(
    "Select Date",
    value=datetime.now().date(),
    min_value=df_sessions_filtered["start_ts"].min().date() if not df_sessions_filtered.empty else datetime.now().date(),
    max_value=datetime.now().date(),
)

st.sidebar.markdown("---")
show_graph = st.sidebar.checkbox("Show Knowledge Graph", value=True)
show_decay = st.sidebar.checkbox("Show Memory Decay", value=True)

# -----------------------------
# Overview Metrics
# -----------------------------
st.subheader("📊 Overview")

if not df_sessions_filtered.empty:
    today_df = df_sessions_filtered[df_sessions_filtered["start_ts"].dt.date == date_filter]
    total_hours = today_df["duration_min"].sum() / 60
    avg_duration = today_df["duration_min"].mean() if not today_df.empty else 0
    sessions_today = len(today_df)
else:
    total_hours = avg_duration = sessions_today = 0

concepts_tracked = len(df_decay["keyword"].unique()) if not df_decay.empty else 0
reminders = len(df_metrics[df_metrics["next_review_time"] > datetime.now()]) if not df_metrics.empty else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Hours Today", f"{total_hours:.2f} h")
c2.metric("Avg. Session", f"{avg_duration:.1f} min")
c3.metric("Tracked Concepts", f"{concepts_tracked}")
c4.metric("Upcoming Reviews", f"{reminders}")

# -----------------------------
# Session Trend
# -----------------------------
if not df_sessions_filtered.empty:
    st.subheader("⏱️ Daily Session Trend")
    df_daily = df_sessions_filtered.groupby(df_sessions_filtered["start_ts"].dt.date)["duration_min"].sum() / 60
    st.line_chart(df_daily, height=200)
else:
    st.info("No session data found.")

# -----------------------------
# Lightweight Knowledge Graph
# -----------------------------
if show_graph:
    st.subheader("🕸️ Knowledge Graph (2D)")
    try:
        sync_db_to_graph()
        G = get_graph()
        if not G.nodes:
            st.info("No nodes available in the graph.")
        else:
            pos = nx.spring_layout(G, seed=42)
            node_scores = [G.nodes[n].get("memory_score", 0.5) for n in G.nodes]
            node_sizes = [200 + 600 * s for s in node_scores]

            edge_x, edge_y = [], []
            for e in G.edges():
                x0, y0 = pos[e[0]]
                x1, y1 = pos[e[1]]
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color="gray", width=1), hoverinfo="none")
            )
            fig.add_trace(
                go.Scatter(
                    x=[pos[n][0] for n in G.nodes()],
                    y=[pos[n][1] for n in G.nodes()],
                    mode="markers+text",
                    text=list(G.nodes()),
                    marker=dict(size=node_sizes, color=node_scores, colorscale="Viridis", showscale=True),
                    textposition="top center",
                )
            )
            fig.update_layout(
                title="Knowledge Graph (Memory Score Intensity)",
                margin=dict(l=10, r=10, t=40, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Graph load failed: {e}")

# -----------------------------
# Memory Decay (Static)
# -----------------------------
if show_decay:
    st.subheader("📉 Memory Decay Curve")
    if not df_decay.empty:
        recent_concepts = df_decay["keyword"].unique()[:5]
        hours = np.linspace(0, 24, 50)
        fig_decay = go.Figure()
        for kw in recent_concepts:
            last_score = df_decay[df_decay["keyword"] == kw]["predicted_recall"].iloc[-1]
            predicted = last_score * np.exp(-0.05 * hours)
            fig_decay.add_trace(
                go.Scatter(
                    x=[datetime.now() + timedelta(hours=h) for h in hours],
                    y=predicted,
                    mode="lines",
                    name=kw,
                )
            )
        fig_decay.update_layout(
            title="Predicted Memory Decay (Next 24 Hours)",
            xaxis_title="Time",
            yaxis_title="Predicted Recall",
            yaxis=dict(range=[0, 1]),
        )
        st.plotly_chart(fig_decay, use_container_width=True)
    else:
        st.info("No memory decay data found.")
