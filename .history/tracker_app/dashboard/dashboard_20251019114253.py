# ==========================================================
# dashboard/fkt_dashboard_litepro.py
# ==========================================================
"""
FKT Dashboard — LitePro Edition
--------------------------------
- Lightweight, responsive, and visually appealing.
- Retains all functional insights (sessions, memory decay, knowledge graph).
- Adds smart new visualizations (radar, timelines, focus clouds).
- Fully optimized for performance (cached reads, minimal loops).
"""

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
st.set_page_config(
    page_title="FKT Dashboard — LitePro",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("⚡ Forgotten Knowledge Tracker — LitePro Dashboard")

# -----------------------------
# Load Data (Cached)
# -----------------------------
@st.cache_data(ttl=180)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
    df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
    conn.close()

    for df in [df_sessions, df_decay, df_metrics]:
        if not df.empty:
            df.replace(["", "null", None], np.nan, inplace=True)

    if not df_sessions.empty:
        df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors="coerce")
        df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors="coerce")
        df_sessions["duration_min"] = (
            (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60
        ).fillna(0)

    return df_sessions, df_decay, df_metrics


df_sessions, df_decay, df_metrics = load_data()

# -----------------------------
# Sidebar Filters
# -----------------------------
st.sidebar.header("🔍 Filters & Controls")

if not df_sessions.empty:
    min_date = df_sessions["start_ts"].min().date()
    max_date = df_sessions["start_ts"].max().date()
else:
    min_date = max_date = datetime.now().date()

date_range = st.sidebar.date_input("Date Range", (min_date, max_date))
show_graph = st.sidebar.checkbox("Show Knowledge Graph", value=True)
show_decay = st.sidebar.checkbox("Show Memory Decay", value=True)
show_focus = st.sidebar.checkbox("Show Focus Radar", value=True)

# -----------------------------
# Overview Metrics
# -----------------------------
st.subheader("📊 Overview")

if not df_sessions.empty:
    mask = (df_sessions["start_ts"].dt.date >= date_range[0]) & (
        df_sessions["start_ts"].dt.date <= date_range[-1]
    )
    df_filtered = df_sessions.loc[mask]
else:
    df_filtered = pd.DataFrame()

total_sessions = len(df_filtered)
total_hours = df_filtered["duration_min"].sum() / 60 if not df_filtered.empty else 0
avg_duration = df_filtered["duration_min"].mean() if not df_filtered.empty else 0
unique_apps = df_filtered["app_name"].nunique() if not df_filtered.empty else 0
concepts_tracked = len(df_decay["keyword"].unique()) if not df_decay.empty else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🕓 Total Hours", f"{total_hours:.2f} h")
c2.metric("📂 Sessions", total_sessions)
c3.metric("💡 Avg. Duration", f"{avg_duration:.1f} min")
c4.metric("🧭 Active Apps", unique_apps)
c5.metric("🧠 Concepts Tracked", concepts_tracked)

# -----------------------------
# Session Trend (Smooth)
# -----------------------------
st.markdown("### ⏱️ Productivity Timeline")
if not df_filtered.empty:
    df_daily = df_filtered.groupby(df_filtered["start_ts"].dt.date)["duration_min"].sum().reset_index()
    df_daily["duration_hr"] = df_daily["duration_min"] / 60
    fig = px.area(
        df_daily,
        x="start_ts",
        y="duration_hr",
        title="Daily Focus Duration",
        color_discrete_sequence=["#636EFA"],
    )
    fig.update_traces(mode="lines+markers", fill="tozeroy")
    fig.update_layout(yaxis_title="Hours", xaxis_title="Date")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No session data available.")

# -----------------------------
# Focus Radar (By Application)
# -----------------------------
if show_focus and not df_filtered.empty:
    st.markdown("### 🎯 Focus Radar — Top Applications")
    app_durations = (
        df_filtered.groupby("app_name")["duration_min"].sum().sort_values(ascending=False).head(5)
    )
    fig_radar = go.Figure()
    categories = app_durations.index.tolist()
    values = app_durations.values.tolist()
    fig_radar.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name="Focus Distribution",
            marker_color="#00CC96",
        )
    )
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=False,
    )
    st.plotly_chart(fig_radar, use_container_width=True)

# -----------------------------
# Knowledge Graph (2D)
# -----------------------------
if show_graph:
    st.markdown("### 🕸️ Knowledge Graph (Semantic Links)")
    try:
        sync_db_to_graph()
        G = get_graph()
        if not G.nodes:
            st.info("No nodes available.")
        else:
            pos = nx.spring_layout(G, seed=7)
            node_scores = [G.nodes[n].get("memory_score", 0.5) for n in G.nodes]
            node_sizes = [300 + 800 * s for s in node_scores]

            edge_x, edge_y = [], []
            for e in G.edges():
                x0, y0 = pos[e[0]]
                x1, y1 = pos[e[1]]
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color="#BBBBBB", width=1)))
            fig.add_trace(
                go.Scatter(
                    x=[pos[n][0] for n in G.nodes()],
                    y=[pos[n][1] for n in G.nodes()],
                    mode="markers+text",
                    text=list(G.nodes()),
                    marker=dict(
                        size=node_sizes,
                        color=node_scores,
                        colorscale="Viridis",
                        showscale=True,
                        colorbar_title="Memory",
                    ),
                    textposition="top center",
                )
            )
            fig.update_layout(
                margin=dict(l=10, r=10, t=40, b=10),
                title="Concept Relations (Semantic Strength)",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Error loading graph: {e}")

# -----------------------------
# Memory Decay
# -----------------------------
if show_decay and not df_decay.empty:
    st.markdown("### 🧠 Memory Decay Over Time")
    recent = df_decay.sort_values("updated_at").groupby("keyword").tail(1)
    fig_decay = px.bar(
        recent,
        x="keyword",
        y="predicted_recall",
        color="predicted_recall",
        color_continuous_scale="Viridis",
        title="Current Recall Predictions",
    )
    fig_decay.update_layout(yaxis_title="Recall Probability", xaxis_title="Keyword")
    st.plotly_chart(fig_decay, use_container_width=True)
else:
    st.info("No decay data available.")

# -----------------------------
# Summary Insight Cards
# -----------------------------
st.markdown("### 📋 Quick Insights")
if not df_filtered.empty:
    top_app = df_filtered.groupby("app_name")["duration_min"].sum().idxmax()
    st.success(f"**Most active app:** {top_app}")
    peak_hour = (
        df_filtered["start_ts"].dt.hour.value_counts().idxmax()
        if not df_filtered.empty
        else "N/A"
    )
    st.info(f"**Peak focus hour:** {peak_hour}:00 hrs")
else:
    st.warning("No session data to summarize.")
