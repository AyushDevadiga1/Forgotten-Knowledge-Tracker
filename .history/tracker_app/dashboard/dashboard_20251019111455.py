# ==========================================================
# dashboard.py | Ultimate Forgotten Knowledge Tracker
# ==========================================================
import sys, os, sqlite3
from datetime import datetime, timedelta
from collections import Counter
import re

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Optional: WordCloud for OCR visualization
try:
    from wordcloud import WordCloud
except ImportError:
    WordCloud = None

# Fix font warnings in matplotlib
plt.rcParams['font.sans-serif'] = ['Arial']

# -----------------------------
# Project Root & Path Setup
# -----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Streamlit Page Setup
# -----------------------------
st.set_page_config(page_title="🔮 Forgotten Knowledge Tracker", layout="wide")
st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Visualize sessions, memory scores, knowledge graphs, reminders, and more.")

# -----------------------------
# Utility: Load & Clean DB Data
# -----------------------------
@st.cache_data(ttl=600)
def load_cleaned_data():
    conn = sqlite3.connect(DB_PATH)
    
    # Sessions
    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors='coerce')
    df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors='coerce')
    df_sessions["app_name"] = df_sessions["app_name"].fillna("Unknown App")
    df_sessions["audio_label"] = df_sessions["audio_label"].fillna("N/A")
    df_sessions["intent_label"] = df_sessions["intent_label"].fillna("N/A")
    df_sessions["intent_confidence"] = pd.to_numeric(df_sessions["intent_confidence"], errors='coerce').fillna(0)
    df_sessions["duration_min"] = (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60

    # Multi-Modal Logs
    df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors='coerce')

    # Memory Decay
    df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
    df_decay["last_seen_ts"] = pd.to_datetime(df_decay["last_seen_ts"], errors='coerce')
    df_decay["updated_at"] = pd.to_datetime(df_decay["updated_at"], errors='coerce')

    # Metrics / Reminders
    df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
    df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors='coerce')

    conn.close()
    return df_sessions, df_logs, df_decay, df_metrics

df_sessions, df_logs, df_decay, df_metrics = load_cleaned_data()

# -----------------------------
# Sidebar / Settings
# -----------------------------
st.sidebar.title("Tracker Settings")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Graph Settings")
node_min_size = st.sidebar.slider("Min Node Size", 100, 500, 200)
node_max_size = st.sidebar.slider("Max Node Size", 500, 2000, 800)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.1, 1.0, 0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("Other Options")
show_3d_labels = st.sidebar.checkbox("Show Labels on 3D Graph", value=True)
# ==========================================================
# Part 2: Main Tabs
# ==========================================================

# -----------------------------
# Create Tabs
# -----------------------------
tabs = st.tabs([
    "📊 Overview", 
    "🕸️ Knowledge Graph", 
    "🧩 3D Graph", 
    "⏱️ Sessions",
    "📉 Memory Decay", 
    "📈 Predicted Forgetting",
    "🎤 Multi-Modal Logs", 
    "⏰ Upcoming Reminders"
])

# -----------------------------
# 1️⃣ Overview Tab
# -----------------------------
with tabs[0]:
    st.subheader("Dashboard Overview")
    
    df_sess_filtered = df_sessions.dropna(subset=["start_ts","end_ts"])
    
    total_hours = df_sess_filtered["duration_min"].sum() / 60 if not df_sess_filtered.empty else 0
    avg_session = df_sess_filtered["duration_min"].mean() if not df_sess_filtered.empty else 0
    num_sessions = len(df_sess_filtered)
    unique_apps = df_sess_filtered["app_name"].nunique() if not df_sess_filtered.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Hours", f"{total_hours:.2f} h")
    col2.metric("Avg Session", f"{avg_session:.1f} min")
    col3.metric("Sessions Count", f"{num_sessions}")
    col4.metric("Unique Apps", f"{unique_apps}")

    if not df_sess_filtered.empty:
        daily_hours = df_sess_filtered.groupby(df_sess_filtered["start_ts"].dt.date)["duration_min"].sum() / 60
        st.line_chart(daily_hours, height=200, use_container_width=True)

    st.markdown("---")
    st.subheader("Top Concepts & Activity")
    
    top_intents = df_sess_filtered["intent_label"].value_counts().head(10)
    top_audio = df_sess_filtered["audio_label"].value_counts().head(10)
    
    c1, c2 = st.columns(2)
    c1.bar_chart(top_intents)
    c2.bar_chart(top_audio)

# -----------------------------
# 2️⃣ Knowledge Graph Tab (2D)
# -----------------------------
with tabs[1]:
    st.subheader("Knowledge Graph (2D)")
    
    sync_db_to_graph()
    G = get_graph()
    
    if G.nodes:
        memory_scores = [G.nodes[n].get('memory_score', 0.3) for n in G.nodes]
        cmap = cm.viridis
        norm = mcolors.Normalize(vmin=0, vmax=1)
        node_colors = [cmap(norm(score)) for score in memory_scores]
        node_sizes = [node_min_size + (node_max_size - node_min_size) * score for score in memory_scores]

        fig, ax = plt.subplots(figsize=(12,10))
        pos = nx.spring_layout(G, seed=42, k=0.8)
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)
        nx.draw_networkx_edges(G, pos, alpha=edge_alpha, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=10, ax=ax)
        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        fig.colorbar(sm, ax=ax, label="Memory Score")
        st.pyplot(fig)
    else:
        st.info("Knowledge graph empty. Add some sessions to visualize.")

# -----------------------------
# 3️⃣ 3D Knowledge Graph Tab
# -----------------------------
with tabs[2]:
    st.subheader("3D Knowledge Graph (Intent → Keywords)")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT intent_label FROM sessions WHERE intent_label IS NOT NULL")
    intents = [row[0] for row in cursor.fetchall()]

    edges = []
    nodes = set()
    for intent in intents:
        cursor.execute("SELECT DISTINCT audio_label || '_' || rowid FROM sessions WHERE intent_label=?", (intent,))
        keywords = [row[0] for row in cursor.fetchall()]
        for kw in keywords:
            edges.append((intent, kw))
            nodes.add(intent)
            nodes.add(kw)
    conn.close()

    if edges:
        G3d = nx.Graph()
        G3d.add_edges_from(edges)
        pos_3d = nx.spring_layout(G3d, dim=3, seed=42)

        x_nodes = [pos_3d[n][0] for n in G3d.nodes()]
        y_nodes = [pos_3d[n][1] for n in G3d.nodes()]
        z_nodes = [pos_3d[n][2] for n in G3d.nodes()]
        labels = list(G3d.nodes()) if show_3d_labels else [""]*len(G3d.nodes())

        edge_x, edge_y, edge_z = [], [], []
        for edge in G3d.edges():
            x0, y0, z0 = pos_3d[edge[0]]
            x1, y1, z1 = pos_3d[edge[1]]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]
            edge_z += [z0, z1, None]

        fig_3d = go.Figure()
        fig_3d.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(color='black', width=2),
            hoverinfo='none'
        ))
        fig_3d.add_trace(go.Scatter3d(
            x=x_nodes, y=y_nodes, z=z_nodes,
            mode='markers+text',
            marker=dict(size=8, color='orange'),
            text=labels,
            textposition='top center'
        ))
        fig_3d.update_layout(
            scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z'),
            height=700,
            title="3D Knowledge Graph"
        )
        st.plotly_chart(fig_3d, use_container_width=True)
    else:
        st.info("No intents or keywords found in DB.")