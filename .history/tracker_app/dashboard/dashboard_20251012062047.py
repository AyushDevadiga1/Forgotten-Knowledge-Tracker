# dashboard/dashboard.py
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

# -----------------------------
# Project Root & Paths
# -----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Streamlit Page Setup
# -----------------------------
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide")
st.markdown("""
<style>
.main { background-color: #0e1117; color: #e1e1e1; }
.stButton>button { background-color: #1f2330; color: #e1e1e1; }
</style>
""", unsafe_allow_html=True)
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

st.sidebar.subheader("Data Filters")
date_range = st.sidebar.date_input("Filter Sessions by Date Range",
                                   [datetime.now() - timedelta(days=30), datetime.now()])

# -----------------------------
# Utility: Load & Clean Data
# -----------------------------
@st.cache_data(ttl=300)
def load_cleaned_data():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Sessions
        df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
        df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors='coerce')
        df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors='coerce')
        df_sessions["app_name"] = df_sessions["app_name"].fillna("Unknown App")

        # Multi-Modal Logs
        df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
        df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors='coerce')

        # Memory Decay
        df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
        df_decay["last_seen_ts"] = pd.to_datetime(df_decay["last_seen_ts"], errors='coerce')
        df_decay["updated_at"] = pd.to_datetime(df_decay["updated_at"], errors='coerce')

        # Metrics / Reminders
        df_metrics = pd.read_sql("SELECT concept, next_review_time, memory_score FROM metrics", conn)
        df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors='coerce')

        return df_sessions, df_logs, df_decay, df_metrics
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    finally:
        conn.close()

df_sessions, df_logs, df_decay, df_metrics = load_cleaned_data()

# Filter sessions by sidebar date range
if not df_sessions.empty:
    start_date, end_date = date_range
    df_sessions = df_sessions[(df_sessions["start_ts"].dt.date >= start_date) & 
                              (df_sessions["start_ts"].dt.date <= end_date)]

# -----------------------------
# Tabs Setup
# -----------------------------
tabs = st.tabs([
    "Overview", "Knowledge Graph", "Sessions",
    "Memory Decay", "Predicted Forgetting",
    "Multi-Modal Logs", "Upcoming Reminders"
])

# -----------------------------
# Fetch Memory Decay Data
# -----------------------------
@st.cache_data(ttl=300)
def fetch_decay(concept=None):
    conn = sqlite3.connect(DB_PATH)
    try:
        if concept:
            df = pd.read_sql(
                "SELECT concept, last_seen_ts AS timestamp, predicted_recall AS memory_score "
                "FROM memory_decay WHERE concept = ? ORDER BY last_seen_ts ASC",
                conn, params=(concept,)
            )
        else:
            df = pd.read_sql(
                "SELECT concept, last_seen_ts AS timestamp, predicted_recall AS memory_score "
                "FROM memory_decay ORDER BY last_seen_ts ASC",
                conn
            )
        return df
    finally:
        conn.close()

# -----------------------------
# Overview Tab
# -----------------------------
with tabs[0]:
    st.subheader("📊 Dashboard Overview")
    df_sessions_filtered = df_sessions.dropna(subset=["start_ts", "end_ts"])
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

    st.markdown("---")
    st.subheader("🧠 Memory Scores")
    try:
        sync_db_to_graph()
        G = get_graph()
    except Exception as e:
        st.error(f"Knowledge graph error: {e}")
        G = nx.Graph()

    if G.nodes:
        mem_table = [{"Concept": node,
                      "Memory Score": round(G.nodes[node].get("memory_score", 0.3), 2),
                      "Next Review": G.nodes[node].get("next_review_time", "N/A")}
                     for node in G.nodes]
        df_mem = pd.DataFrame(mem_table).sort_values("Memory Score")
        st.dataframe(df_mem.style.background_gradient(subset=["Memory Score"], cmap="viridis"))

        # Top 3 concepts
        top3 = df_mem.sort_values("Memory Score", ascending=False).head(3)
        st.subheader("Top Concepts")
        c1, c2, c3 = st.columns(3)
        for idx, col in enumerate([c1, c2, c3]):
            if idx < len(top3):
                concept = top3.iloc[idx]["Concept"]
                score = top3.iloc[idx]["Memory Score"]
                next_r = top3.iloc[idx]["Next Review"]
                col.markdown(f"**{concept}**")
                col.metric("Memory Score", f"{score:.2f}")
                col.markdown(f"Next Review: {next_r}")
    else:
        st.info("No concepts found in the knowledge graph yet.")

# -----------------------------
# Knowledge Graph Tab
# -----------------------------
with tabs[1]:
    st.subheader("🕸️ Knowledge Graph")
    if G.nodes:
        memory_scores = [G.nodes[n].get('memory_score', 0.3) for n in G.nodes]
        cmap = cm.plasma
        norm = mcolors.Normalize(vmin=0, vmax=1)
        node_colors = [cmap(norm(score)) for score in memory_scores]
        node_sizes = [node_min_size + (node_max_size - node_min_size) * score for score in memory_scores]

        # Interactive Network Graph with Plotly
        pos = nx.spring_layout(G, seed=42, k=0.8)
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]
            x1, y1 = pos[e[1]]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='gray'),
            hoverinfo='none',
            mode='lines'
        )

        node_x, node_y, node_text = [], [], []
        for node in G.nodes:
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(f"{node}<br>Memory: {G.nodes[node].get('memory_score',0.3):.2f}")

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=[n for n in G.nodes],
            hovertext=node_text,
            hoverinfo='text',
            marker=dict(
                showscale=True,
                colorscale='Plasma',
                color=memory_scores,
                size=node_sizes,
                colorbar=dict(title='Memory Score'),
                line_width=2
            )
        )

        fig_graph = go.Figure(data=[edge_trace, node_trace])
        fig_graph.update_layout(showlegend=False)
        st.plotly_chart(fig_graph, use_container_width=True)
    else:
        st.info("Knowledge graph empty.")

