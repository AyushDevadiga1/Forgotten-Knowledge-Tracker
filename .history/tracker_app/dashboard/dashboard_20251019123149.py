# dashboard/dashboard.py
"""
🔮 Forgotten Knowledge Tracker - Upgraded Dashboard
Features:
- Modern KPIs, interactive graphs, 3D Knowledge Graph
- Radar charts for memory decay
- Heatmaps for app usage & interaction rate
- Timelines for sessions & multi-modal logs
- Predicted forgetting overlays
"""

import sys, os, sqlite3
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import time

plt.rcParams['font.sans-serif'] = ['Arial']

# Project Root
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Utility: Load & Clean Data
# -----------------------------
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
# Streamlit Page Setup
# -----------------------------
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide")
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

# -----------------------------
# KPI Metrics
# -----------------------------
total_concepts = len(df_decay['keyword'].unique())
avg_memory_score = df_decay['predicted_recall'].mean() if not df_decay.empty else 0
upcoming_reviews = df_metrics[df_metrics["next_review_time"] > datetime.now()].shape[0]

col1, col2, col3 = st.columns(3)
col1.metric("Total Concepts", total_concepts)
col2.metric("Avg Memory Score", f"{avg_memory_score:.2f}")
col3.metric("Upcoming Reviews", upcoming_reviews)

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
        st.info("Knowledge graph empty.")

# -----------------------------
# 3D Knowledge Graph Tab
# -----------------------------
# -----------------------------
# 3D Knowledge Graph by Intent Tab
# -----------------------------
# -----------------------------
# Unified 3D Knowledge Graph (All Intents)
# -----------------------------
with tabs[2]:
    st.subheader("🧩 Unified 3D Knowledge Graph: All Intents")
    
    df_intents = df_sessions.dropna(subset=['intent_label'])
    intents = df_intents['intent_label'].unique()
    
    if len(intents) == 0:
        st.info("No intents found in DB.")
    else:
        # Assign a unique color to each intent
        color_map = px.colors.qualitative.Safe
        intent_colors = {intent: color_map[i % len(color_map)] for i, intent in enumerate(intents)}
        
        # Build edges and nodes
        edges = []
        nodes = {}
        for _, row in df_intents.iterrows():
            node_name = f"{row['audio_label']}_{row['id']}"
            intent = row['intent_label']
            edges.append((intent, node_name))
            nodes[node_name] = intent
            nodes[intent] = intent  # ensure intent nodes exist

        if edges:
            G3d = nx.Graph()
            G3d.add_edges_from(edges)
            pos_3d = nx.spring_layout(G3d, dim=3, seed=42, k=0.5)

            x_nodes = [pos_3d[n][0] for n in G3d.nodes()]
            y_nodes = [pos_3d[n][1] for n in G3d.nodes()]
            z_nodes = [pos_3d[n][2] for n in G3d.nodes()]
            labels = list(G3d.nodes())
            node_colors = [intent_colors[nodes[n]] for n in G3d.nodes()]

            # edges
            edge_x, edge_y, edge_z = [], [], []
            for e in G3d.edges():
                x0, y0, z0 = pos_3d[e[0]]
                x1, y1, z1 = pos_3d[e[1]]
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]
                edge_z += [z0, z1, None]

            fig_3d = go.Figure()
            # Add edges
            fig_3d.add_trace(go.Scatter3d(
                x=edge_x, y=edge_y, z=edge_z,
                mode='lines',
                line=dict(color='gray', width=2),
                hoverinfo='none'
            ))

            # Add nodes with colors
            fig_3d.add_trace(go.Scatter3d(
                x=x_nodes, y=y_nodes, z=z_nodes,
                mode='markers+text',
                marker=dict(
                    size=8,
                    color=node_colors,
                    line=dict(width=1, color='black')
                ),
                text=labels,
                textposition='top center',
                textfont=dict(size=10),
                hoverinfo='text'
            ))

            fig_3d.update_layout(
                title="3D Knowledge Graph: All Final Intents",
                scene=dict(
                    xaxis=dict(title='X'),
                    yaxis=dict(title='Y'),
                    zaxis=dict(title='Z')
                ),
                height=750,
                margin=dict(l=0, r=0, b=0, t=50)
            )
            st.plotly_chart(fig_3d, use_container_width=True)
        else:
            st.info("No keywords found for any intent.")

# -----------------------------
# Sessions Timeline & Heatmap
# -----------------------------
with tabs[3]:
    st.subheader("⏱️ Session Timeline & Heatmap")
    if not df_sessions_filtered.empty:
        df_sess = df_sessions_filtered.copy()
        df_sess["end_ts"] = df_sess["end_ts"].where(df_sess["end_ts"]>df_sess["start_ts"], df_sess["start_ts"]+pd.Timedelta(seconds=5))
        df_sess["duration"] = (df_sess["end_ts"]-df_sess["start_ts"]).dt.total_seconds()/60

        # Timeline
        fig_tl = px.timeline(df_sess, x_start="start_ts", x_end="end_ts", y="app_name", color="app_name")
        fig_tl.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_tl, use_container_width=True)

        # Heatmap
        heat_df = df_sess.groupby(["app_name", df_sess["start_ts"].dt.date])["duration"].sum().reset_index()
        heat_pivot = heat_df.pivot(index="app_name", columns="start_ts", values="duration").fillna(0)
        fig_hm = go.Figure(data=go.Heatmap(
            z=heat_pivot.values,
            x=[str(d) for d in heat_pivot.columns],
            y=heat_pivot.index,
            colorscale="Viridis",
            hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} min<extra></extra>"
        ))
        fig_hm.update_layout(title="App Usage Heatmap", height=400)
        st.plotly_chart(fig_hm, use_container_width=True)

# -----------------------------
# Memory Decay Tab (Clean 3D alternative)
# -----------------------------
# -----------------------------
# Memory Decay 3D Visualization
# -----------------------------
with tabs[4]:
    st.subheader("📉 Memory Decay Over Time (3D View)")

    if not df_decay.empty:
        # Ensure keywords have an index for y-axis
        unique_keywords = df_decay['keyword'].unique()
        keyword_to_idx = {k: i for i, k in enumerate(unique_keywords)}

        fig_decay = go.Figure()

        for kw in unique_keywords:
            df_kw = df_decay[df_decay['keyword'] == kw].sort_values('last_seen_ts')
            fig_decay.add_trace(go.Scatter3d(
                x=df_kw['last_seen_ts'],
                y=[keyword_to_idx[kw]] * len(df_kw),
                z=df_kw['predicted_recall'],
                mode='lines+markers+text',
                text=[kw] * len(df_kw),
                textposition='top center',
                line=dict(width=3),
                marker=dict(size=5),
                name=kw,
                hovertemplate="Keyword: %{text}<br>Time: %{x}<br>Recall: %{z:.2f}<extra></extra>"
            ))

        fig_decay.update_layout(
            title="Memory Decay Curves for All Keywords",
            scene=dict(
                xaxis=dict(title='Time'),
                yaxis=dict(title='Keyword Index', tickvals=list(keyword_to_idx.values()),
                           ticktext=list(keyword_to_idx.keys())),
                zaxis=dict(title='Predicted Recall', range=[0, 1])
            ),
            height=750,
            margin=dict(l=0, r=0, b=0, t=50)
        )

        st.plotly_chart(fig_decay, use_container_width=True)
    else:
        st.info("No memory decay data available.")


# -----------------------------
# Predicted Forgetting
# -----------------------------
with tabs[5]:
    st.subheader("📈 Predicted Forgetting Overlay")
    if not df_decay.empty:
        selected_pred = st.selectbox("Choose concept", df_decay["keyword"].unique())
        df_last = df_decay[df_decay["keyword"]==selected_pred]
        last_score = df_last["predicted_recall"].iloc[-1] if not df_last.empty else 0.5
        times = np.linspace(0, 24, 50)
        predicted_scores = last_score*np.exp(-0.1*times)
        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=[datetime.now()+timedelta(hours=t) for t in times],
            y=predicted_scores, mode="lines+markers",
            line=dict(color='orange', width=3)
        ))
        fig_pred.update_layout(yaxis=dict(range=[0,1]), xaxis_title="Time", yaxis_title="Memory Score",
                               title=f"Predicted Forgetting Curve for {selected_pred}", height=500)
        st.plotly_chart(fig_pred, use_container_width=True)
    else:
        st.info("No decay data for prediction.")

# -----------------------------
# Multi-Modal Logs
# -----------------------------
with tabs[6]:
    st.subheader("🎤 Multi-Modal Logs")
    if not df_logs.empty:
        st.dataframe(df_logs.head(100))
    else:
        st.info("No multi-modal logs available.")

# -----------------------------
# Upcoming Reminders
# -----------------------------
with tabs[7]:
    st.subheader("⏰ Upcoming Reminders")
    now = datetime.now()
    upcoming = df_metrics[df_metrics["next_review_time"]>now].sort_values("next_review_time").head(20)
    if not upcoming.empty:
        st.dataframe(upcoming[["concept","next_review_time","memory_score"]])
    else:
        st.info("No upcoming reminders.")
