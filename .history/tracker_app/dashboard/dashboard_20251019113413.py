# ==========================================================
# dashboard_animated.py | Animated Stylish FKT Dashboard
# ==========================================================

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
from matplotlib import cm
from matplotlib import colors as mcolors
import time

# -----------------------------
# Project Root
# -----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Streamlit Page Setup
# -----------------------------
st.set_page_config(page_title="🔮 FKT Dashboard Animated", layout="wide")
st.title("🔮 Forgotten Knowledge Tracker - Animated")
st.markdown("Interactive visualization with animated 3D graph and memory decay simulation.")

# -----------------------------
# Load Data
# -----------------------------
@st.cache_data(ttl=60)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    # Sessions
    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors='coerce')
    df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors='coerce')
    df_sessions["duration_min"] = (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds()/60
    df_sessions["app_name"] = df_sessions["app_name"].fillna("Unknown")
    df_sessions["audio_label"] = df_sessions["audio_label"].fillna("N/A")
    df_sessions["intent_label"] = df_sessions["intent_label"].fillna("N/A")
    df_sessions["intent_confidence"] = pd.to_numeric(df_sessions["intent_confidence"], errors='coerce').fillna(0)

    # Multi-modal logs
    df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors='coerce')

    # Memory decay
    df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
    df_decay["last_seen_ts"] = pd.to_datetime(df_decay["last_seen_ts"], errors='coerce')
    df_decay["updated_at"] = pd.to_datetime(df_decay["updated_at"], errors='coerce')

    # Metrics
    df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
    df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors='coerce')

    conn.close()
    return df_sessions, df_logs, df_decay, df_metrics

df_sessions, df_logs, df_decay, df_metrics = load_data()
df_sessions_filtered = df_sessions.dropna(subset=["start_ts","end_ts"])

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Settings")
enable_webcam = st.sidebar.checkbox("Enable Webcam", value=False)
enable_audio = st.sidebar.checkbox("Enable Audio", value=True)
enable_screenshots = st.sidebar.checkbox("Enable Screenshots", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Graph Settings")
node_min_size = st.sidebar.slider("Min Node Size", 50, 500, 150)
node_max_size = st.sidebar.slider("Max Node Size", 500, 2500, 800)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.1, 1.0, 0.6)

st.sidebar.markdown("---")
st.sidebar.subheader("Animation Settings")
anim_speed = st.sidebar.slider("Animation Speed (s)", 0.1, 2.0, 0.5)

# -----------------------------
# Tabs
# -----------------------------
tabs = ["Overview", "2D Graph", "3D Graph", "Sessions", "Memory Decay", "Predicted Forgetting", "Logs", "Reminders"]
current_tab = st.sidebar.radio("Select Tab", tabs)

# ==========================================================
# TAB 1: Overview
# ==========================================================
if current_tab == "Overview":
    st.subheader("📊 Overview Metrics")
    total_hours = df_sessions_filtered["duration_min"].sum()/60 if not df_sessions_filtered.empty else 0
    avg_session = df_sessions_filtered["duration_min"].mean() if not df_sessions_filtered.empty else 0
    num_sessions = len(df_sessions_filtered)
    num_concepts = len(df_decay["keyword"].unique()) if not df_decay.empty else 0
    upcoming_reminders = len(df_metrics[df_metrics["next_review_time"] > datetime.now()])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Hours", f"{total_hours:.2f} h", delta=f"{avg_session:.1f} min/session")
    col2.metric("Sessions Count", num_sessions)
    col3.metric("Tracked Concepts", num_concepts)
    col4.metric("Upcoming Reviews", upcoming_reminders)

    if not df_sessions_filtered.empty:
        daily_hours = df_sessions_filtered.groupby(df_sessions_filtered["start_ts"].dt.date)["duration_min"].sum()/60
        st.line_chart(daily_hours, height=200)

# ==========================================================
# TAB 2: 2D Knowledge Graph
# ==========================================================
if current_tab == "2D Graph":
    st.subheader("🕸️ Knowledge Graph")
    sync_db_to_graph()
    G = get_graph()
    if G.nodes:
        memory_scores = [G.nodes[n].get('memory_score',0.3) for n in G.nodes]
        cmap = cm.viridis
        norm = mcolors.Normalize(vmin=0, vmax=1)
        node_colors = [cmap(norm(score)) for score in memory_scores]
        node_sizes = [node_min_size + (node_max_size-node_min_size)*score for score in memory_scores]

        pos = nx.spring_layout(G, seed=42)
        edge_x, edge_y = [], []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x += [x0,x1,None]; edge_y += [y0,y1,None]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='gray'),
                                 hoverinfo='none', mode='lines'))
        fig.add_trace(go.Scatter(x=[pos[n][0] for n in G.nodes()],
                                 y=[pos[n][1] for n in G.nodes()],
                                 mode='markers+text',
                                 marker=dict(size=node_sizes, color=memory_scores, colorscale='Viridis', showscale=True),
                                 text=list(G.nodes()), textposition='top center'))
        fig.update_layout(title="2D Knowledge Graph", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No nodes found.")

# ==========================================================
# TAB 3: Animated 3D Knowledge Graph
# ==========================================================
if current_tab == "3D Graph":
    st.subheader("🧩 Animated 3D Knowledge Graph")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT intent_label FROM sessions WHERE intent_label IS NOT NULL")
    intents = [r[0] for r in cursor.fetchall()]
    edges, nodes = [], set()
    for intent in intents:
        cursor.execute("SELECT DISTINCT audio_label || '_' || rowid FROM sessions WHERE intent_label=?", (intent,))
        keywords = [r[0] for r in cursor.fetchall()]
        for kw in keywords:
            edges.append((intent, kw))
            nodes.add(intent)
            nodes.add(kw)
    conn.close()

    if edges:
        G3d = nx.Graph()
        G3d.add_edges_from(edges)
        pos_3d = nx.spring_layout(G3d, dim=3, seed=42)
        x_nodes = np.array([pos_3d[n][0] for n in G3d.nodes()])
        y_nodes = np.array([pos_3d[n][1] for n in G3d.nodes()])
        z_nodes = np.array([pos_3d[n][2] for n in G3d.nodes()])

        fig_3d = go.Figure()
        # Animate nodes with small random movement
        for i in range(10):
            x_anim = x_nodes + np.random.normal(0,0.02,len(x_nodes))
            y_anim = y_nodes + np.random.normal(0,0.02,len(y_nodes))
            z_anim = z_nodes + np.random.normal(0,0.02,len(z_nodes))
            fig_3d.add_trace(go.Scatter3d(x=x_anim, y=y_anim, z=z_anim, mode='markers+text',
                                          marker=dict(size=8,color='orange'),
                                          text=list(G3d.nodes()), textposition='top center'))
            st.plotly_chart(fig_3d, use_container_width=True)
            time.sleep(anim_speed)
    else:
        st.info("No intents/keywords found.")

# ==========================================================
# TAB 4: Memory Decay Animation
# ==========================================================
if current_tab == "Memory Decay":
    st.subheader("📉 Animated Memory Decay")
    if not df_decay.empty:
        selected_concepts = st.multiselect("Select concepts to animate", df_decay["keyword"].unique(), default=df_decay["keyword"].unique()[:3])
        hours = np.linspace(0,48,50)
        fig_decay = go.Figure()
        for concept in selected_concepts:
            last_score = df_decay[df_decay["keyword"]==concept]["predicted_recall"].iloc[-1]
            predicted = last_score*np.exp(-0.05*hours)
            fig_decay.add_trace(go.Scatter(x=[datetime.now()+timedelta(hours=h) for h in hours],
                                           y=predicted,
                                           mode='lines+markers',
                                           name=concept))
        fig_decay.update_layout(yaxis=dict(range=[0,1]), xaxis_title="Time", yaxis_title="Memory Score")
        st.plotly_chart(fig_decay, use_container_width=True)
    else:
        st.info("No decay data.")

# ==========================================================
# Remaining Tabs: Sessions, Logs, Reminders
# ==========================================================
if current_tab == "Sessions":
    st.subheader("⏱️ Sessions Timeline & Heatmap")
    if not df_sessions_filtered.empty:
        df_sess = df_sessions_filtered.copy()
        df_sess["end_ts"] = df_sess["end_ts"].where(df_sess["end_ts"]>df_sess["start_ts"], df_sess["start_ts"]+pd.Timedelta(seconds=5))
        df_sess["duration"] = (df_sess["end_ts"]-df_sess["start_ts"]).dt.total_seconds()/60
        fig_tl = px.timeline(df_sess, x_start="start_ts", x_end="end_ts", y="app_name", color="app_name")
        fig_tl.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_tl, use_container_width=True)

        heat_df = df_sess.groupby(["app_name", df_sess["start_ts"].dt.date])["duration"].sum().reset_index()
        heat_pivot = heat_df.pivot(index="app_name", columns="start_ts", values="duration").fillna(0)
        fig_hm = go.Figure(data=go.Heatmap(z=heat_pivot.values, x=[str(d) for d in heat_pivot.columns],
                                           y=heat_pivot.index, colorscale='Viridis'))
        st.plotly_chart(fig_hm, use_container_width=True)

if current_tab == "Predicted Forgetting":
    st.subheader("📈 Predicted Forgetting")
    if not df_decay.empty:
        concept = st.selectbox("Select Concept", df_decay["keyword"].unique())
        last_score = df_decay[df_decay["keyword"]==concept]["predicted_recall"].iloc[-1]
        hours = np.linspace(0,24,50)
        predicted_scores = last_score*np.exp(-0.1*hours)
        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(x=[datetime.now()+timedelta(hours=t) for t in hours],
                                      y=predicted_scores, mode='lines+markers', name='Predicted Recall'))
        st.plotly_chart(fig_pred, use_container_width=True)

if current_tab == "Logs":
    st.subheader("🎤 Multi-Modal Logs")
    if not df_logs.empty:
        st.dataframe(df_logs.head(100))

if current_tab == "Reminders":
    st.subheader("⏰ Upcoming Reminders")
    upcoming = df_metrics[df_metrics["next_review_time"] > datetime.now()].sort_values("next_review_time")
    if not upcoming.empty:
        st.dataframe(upcoming[["concept","next_review_time","memory_score"]])
