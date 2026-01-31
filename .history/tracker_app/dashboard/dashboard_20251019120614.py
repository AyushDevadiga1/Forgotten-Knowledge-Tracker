# ==============================================================
# dashboard/dashboard.py — Modernized FKT Dashboard v2.0
# ==============================================================

import sys
import os
import sqlite3
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import time

# Project Root
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Utility: Load & Clean Data
# -----------------------------
@st.cache_data
def load_cleaned_data():
    conn = sqlite3.connect(DB_PATH)
    
    # Sessions
    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors='coerce')
    df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors='coerce')
    df_sessions["app_name"].fillna("Unknown App", inplace=True)
    df_sessions["audio_label"].fillna("N/A", inplace=True)
    df_sessions["intent_label"].fillna("N/A", inplace=True)
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
# Streamlit Page Setup
# -----------------------------
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide")
st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Modern, interactive dashboard with advanced visualizations and knowledge graph insights.")

# -----------------------------
# Sidebar Settings
# -----------------------------
st.sidebar.title("Tracker Settings")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)
st.sidebar.markdown("---")
st.sidebar.subheader("Graph Visual Settings")
node_min_size = st.sidebar.slider("Min Node Size", 5, 50, 15)
node_max_size = st.sidebar.slider("Max Node Size", 50, 200, 60)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.1, 1.0, 0.5)

# -----------------------------
# Tabs
# -----------------------------
tabs = st.tabs([
    "Overview", "Knowledge Graph", "3D Graph", "Sessions",
    "Memory Decay", "Predicted Forgetting",
    "Multi-Modal Logs", "Upcoming Reminders"
])

# -----------------------------
# Overview Tab
# -----------------------------
with tabs[0]:
    st.subheader("📊 Dashboard Overview")
    df_sessions_filtered = df_sessions.dropna(subset=["start_ts","end_ts"])
    total_hours = df_sessions_filtered["duration_min"].sum() / 60 if not df_sessions_filtered.empty else 0
    avg_session = df_sessions_filtered["duration_min"].mean() if not df_sessions_filtered.empty else 0
    num_sessions = len(df_sessions_filtered)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Hours", f"{total_hours:.2f} h")
    col2.metric("Avg Session", f"{avg_session:.1f} min")
    col3.metric("Number of Sessions", f"{num_sessions}")

    if not df_sessions_filtered.empty:
        daily_hours = df_sessions_filtered.groupby(df_sessions_filtered["start_ts"].dt.date)["duration_min"].sum() / 60
        col4.line_chart(daily_hours, height=100)

# -----------------------------
# Knowledge Graph Tab
# -----------------------------
with tabs[1]:
    st.subheader("🕸️ Knowledge Graph")
    sync_db_to_graph()
    G = get_graph()

    if G.nodes:
        memory_scores = [G.nodes[n].get('memory_score', 0.3) for n in G.nodes]
        node_sizes = [node_min_size + (node_max_size - node_min_size) * score for score in memory_scores]
        node_colors = memory_scores

        pos = nx.spring_layout(G, seed=42, k=0.8)
        edge_x = []
        edge_y = []

        for e in G.edges():
            x0, y0 = pos[e[0]]
            x1, y1 = pos[e[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        fig = go.Figure()

        # Edges
        fig.add_trace(go.Scatter(x=edge_x, y=edge_y,
                                 line=dict(width=1, color='rgba(100,100,100,0.5)'),
                                 hoverinfo='none', mode='lines'))

        # Nodes
        node_x = [pos[n][0] for n in G.nodes]
        node_y = [pos[n][1] for n in G.nodes]
        fig.add_trace(go.Scatter(x=node_x, y=node_y,
                                 mode='markers+text',
                                 text=list(G.nodes),
                                 textposition='top center',
                                 marker=dict(size=node_sizes,
                                             color=node_colors,
                                             colorscale='Viridis',
                                             colorbar=dict(title="Memory Score"),
                                             line=dict(width=2, color='DarkSlateGrey'))))
        fig.update_layout(title="2D Knowledge Graph", showlegend=False, height=700)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Knowledge graph empty.")

# -----------------------------
# 3D Knowledge Graph Tab
# -----------------------------
with tabs[2]:
    st.subheader("🧩 3D Knowledge Graph (Intent → Keywords)")

    # Fetch intents & keywords from DB
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
        pos_3d = nx.spring_layout(G3d, dim=3, seed=42, k=0.8)

        x_nodes = [pos_3d[n][0] for n in G3d.nodes()]
        y_nodes = [pos_3d[n][1] for n in G3d.nodes()]
        z_nodes = [pos_3d[n][2] for n in G3d.nodes()]
        labels = list(G3d.nodes())

        # Edges
        edge_x, edge_y, edge_z = [], [], []
        for e in G3d.edges():
            x0, y0, z0 = pos_3d[e[0]]
            x1, y1, z1 = pos_3d[e[1]]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]
            edge_z += [z0, z1, None]

        fig_3d = go.Figure()

        # Add edges
        fig_3d.add_trace(go.Scatter3d(x=edge_x, y=edge_y, z=edge_z,
                                      mode='lines',
                                      line=dict(color='gray', width=2),
                                      hoverinfo='none'))

        # Add nodes
        fig_3d.add_trace(go.Scatter3d(x=x_nodes, y=y_nodes, z=z_nodes,
                                      mode='markers+text',
                                      text=labels,
                                      textposition='top center',
                                      marker=dict(size=8,
                                                  color='orange',
                                                  line=dict(width=1, color='black'))))

        fig_3d.update_layout(scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z'),
                             height=750, title="3D Knowledge Graph: Intent → Keywords",
                             margin=dict(l=0, r=0, b=0, t=50))
        st.plotly_chart(fig_3d, use_container_width=True)
    else:
        st.info("No intents or keywords found in DB.")

# -----------------------------
# Sessions Tab
# -----------------------------
with tabs[3]:
    st.subheader("⏱️ Session Timeline & Heatmap")

    if not df_sessions_filtered.empty:
        df_sess = df_sessions_filtered.copy()
        df_sess["end_ts"] = df_sess["end_ts"].where(df_sess["end_ts"] > df_sess["start_ts"],
                                                    df_sess["start_ts"] + pd.Timedelta(seconds=5))
        df_sess["duration"] = (df_sess["end_ts"] - df_sess["start_ts"]).dt.total_seconds()/60

        # Interactive Timeline
        fig_tl = px.timeline(df_sess, x_start="start_ts", x_end="end_ts", y="app_name",
                             color="app_name", hover_data=["audio_label", "intent_label"])
        fig_tl.update_yaxes(autorange="reversed")
        fig_tl.update_layout(title="Session Timeline", height=500)
        st.plotly_chart(fig_tl, use_container_width=True)

        # Heatmap: App Usage
        heat_df = df_sess.groupby(["app_name", df_sess["start_ts"].dt.date])["duration"].sum().reset_index()
        heat_pivot = heat_df.pivot(index="app_name", columns="start_ts", values="duration").fillna(0)
        fig_hm = go.Figure(data=go.Heatmap(
            z=heat_pivot.values,
            x=[str(d) for d in heat_pivot.columns],
            y=heat_pivot.index,
            colorscale="Viridis",
            hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} min<extra></extra>"
        ))
        fig_hm.update_layout(title="App Usage Duration Heatmap", height=500)
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.info("No session data available.")

# -----------------------------
# Memory Decay Tab
# -----------------------------
with tabs[4]:
    st.subheader("📉 Memory Decay Curves")

    if not df_decay.empty:
        fig_decay = px.line(df_decay, x="last_seen_ts", y="predicted_recall",
                            color="keyword", markers=True,
                            title="Memory Decay Per Concept",
                            labels={"last_seen_ts": "Time", "predicted_recall": "Recall"})
        fig_decay.update_yaxes(range=[0,1])
        st.plotly_chart(fig_decay, use_container_width=True)
    else:
        st.info("No memory decay data found.")

# -----------------------------
# Predicted Forgetting Tab
# -----------------------------
with tabs[5]:
    st.subheader("📈 Predicted Forgetting Overlay")

    if not df_decay.empty:
        selected_pred = st.selectbox("Choose concept", df_decay["keyword"].unique())
        lambda_val = 0.1
        hours = 24
        df_last = df_decay[df_decay["keyword"]==selected_pred]
        last_score = df_last["predicted_recall"].iloc[-1] if not df_last.empty else 0.5
        times = np.linspace(0, hours, 50)
        predicted_scores = last_score * np.exp(-lambda_val * times)

        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=[datetime.now() + timedelta(hours=t) for t in times],
            y=predicted_scores,
            mode="lines+markers",
            name="Predicted Recall",
            line=dict(color='orange', width=3),
            marker=dict(size=6)
        ))
        fig_pred.update_layout(yaxis=dict(range=[0,1]),
                               xaxis_title="Time",
                               yaxis_title="Memory Score",
                               title=f"Predicted Forgetting Curve for {selected_pred}",
                               height=500)
        st.plotly_chart(fig_pred, use_container_width=True)
    else:
        st.info("No decay data for prediction.")

# -----------------------------
# Multi-Modal Logs Tab
# -----------------------------
with tabs[6]:
    st.subheader("🎤 Multi-Modal Logs")
    if not df_logs.empty:
        st.dataframe(df_logs.head(100))
        # Optional: Interactive filtering
        filter_app = st.text_input("Filter by audio_label/app_name", "")
        if filter_app:
            filtered_logs = df_logs[df_logs["audio_label"].str.contains(filter_app, case=False, na=False)]
            st.dataframe(filtered_logs)
    else:
        st.info("No multi-modal logs available.")

# -----------------------------
# Upcoming Reminders Tab
# -----------------------------
with tabs[7]:
    st.subheader("⏰ Upcoming Reminders")
    now = datetime.now()
    upcoming = df_metrics[df_metrics["next_review_time"] > now].sort_values("next_review_time").head(20)

    if not upcoming.empty:
        fig_reminders = go.Figure(data=[go.Table(
            header=dict(values=["Concept", "Next Review Time", "Memory Score"],
                        fill_color='paleturquoise',
                        align='left'),
            cells=dict(values=[upcoming.concept, upcoming.next_review_time, upcoming.memory_score],
                       fill_color='lavender',
                       align='left'))
        ])
        fig_reminders.update_layout(title="Next 20 Reviews", height=400)
        st.plotly_chart(fig_reminders, use_container_width=True)
    else:
        st.info("No upcoming reminders.")

# -----------------------------
with st.spinner("Loading complex 3D graph... this may take a few seconds"):
    time.sleep(2)
