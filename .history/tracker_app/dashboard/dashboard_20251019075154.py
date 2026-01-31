#dashboard/dashboard.py
'''     Make sure after loading the 3d graph wait for few seconds as we are
    loading a lot of nodes in the 3d graph at once .
'''
import sys
import os
import sqlite3
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

# Fix font warnings in matplotlib
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
with tabs[1]:
    st.header("Interactive 3D Knowledge Graph")
    if len(G.nodes) == 0:
        st.info("Knowledge graph is empty. Sync DB to populate nodes.")
    else:
        # Create 3D layout based on spring layout (projected to 3D)
    try:
        pos2d = nx.spring_layout(G, seed=42, k=0.5, iterations=50)
        centrality = nx.degree_centrality(G)
        nodes = list(G.nodes)
        x, y, z, text, size, color = [], [], [], [], [], []
        mem_scores = [float(G.nodes.get(n, {}).get("memory_score", 0.3)) for n in nodes]
        norm = mcolors.Normalize(vmin=0, vmax=1)
        cmap = cm.plasma


        for i, n in enumerate(nodes):
        px_, py_ = pos2d.get(n, (np.random.random(), np.random.random()))
        pz_ = float(centrality.get(n, 0)) * 0.8
        x.append(px_)
        y.append(py_)
        z.append(pz_)
        ms = float(G.nodes.get(n, {}).get("memory_score", 0.3))
        text.append(f"{n}<br>Memory: {ms:.2f}<br>Count: {G.nodes.get(n, {}).get('count',0)}")
        # scale sizes into reasonable marker sizes
        scaled = node_min_size + (node_max_size - node_min_size) * ms
        size.append(float(max(6, scaled)))
        color.append(mcolors.to_hex(cmap(norm(ms))))


        edge_x, edge_y, edge_z = [], [], []
        for n1, n2 in G.edges():
        try:
            edge_x += [pos2d.get(n1, (0, 0))[0], pos2d.get(n2, (0, 0))[0], None]
            edge_y += [pos2d.get(n1, (0, 0))[1], pos2d.get(n2, (0, 0))[1], None]
            edge_z += [centrality.get(n1, 0) * 0.8, centrality.get(n2, 0) * 0.8, None]
        except KeyError:
         continue    


    node_trace = go.Scatter3d(
    x=x, y=y, z=z,
    mode='markers',
    marker=dict(size=[max(6, s / 40) for s in size], color=color, opacity=0.9),
    text=[n for n in nodes],
    hovertext=text,
    hoverinfo='text'
    )


    edge_trace = go.Scatter3d(x=edge_x, y=edge_y, z=edge_z, mode='lines',
    line=dict(width=1, color=f'rgba(150,150,150,{edge_alpha})'))


    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(scene=dict(xaxis=dict(showbackground=False, visible=False),
    yaxis=dict(showbackground=False, visible=False),
    zaxis=dict(showbackground=False, visible=False)),
    margin=dict(l=0, r=0, t=30, b=0),
    showlegend=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")
    except Exception as e:
    st.error(f"Failed to render 3D graph: {e}")
# -----------------------------
# Sessions Tab
# -----------------------------
with tabs[3]:
    st.subheader("⏱️ Session Timeline & Heatmap")
    if not df_sessions_filtered.empty:
        df_sess = df_sessions_filtered.copy()
        df_sess["end_ts"] = df_sess["end_ts"].where(df_sess["end_ts"] > df_sess["start_ts"], df_sess["start_ts"] + pd.Timedelta(seconds=5))
        df_sess["duration"] = (df_sess["end_ts"] - df_sess["start_ts"]).dt.total_seconds()/60

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
        fig_hm.update_layout(title="App Usage Duration Heatmap")
        st.plotly_chart(fig_hm, use_container_width=True)

# -----------------------------
# Memory Decay Tab
# -----------------------------
with tabs[4]:
    st.subheader("📉 Memory Decay Curves")

    if not df_decay.empty:
        fig_decay = px.line(df_decay, x="last_seen_ts", y="predicted_recall", color="keyword", markers=True,
                            title="Memory Decay Per Concept", labels={"last_seen_ts":"Time","predicted_recall":"Recall"})
        fig_decay.update_layout(yaxis=dict(range=[0,1]))
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
            mode="lines",
            name="Predicted Recall"
        ))
        fig_pred.update_layout(yaxis=dict(range=[0,1]), xaxis_title="Time", yaxis_title="Memory Score",
                               title=f"Predicted Forgetting Curve for {selected_pred}")
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
        st.dataframe(upcoming[["concept","next_review_time","memory_score"]])
    else:
        st.info("No upcoming reminders.")
