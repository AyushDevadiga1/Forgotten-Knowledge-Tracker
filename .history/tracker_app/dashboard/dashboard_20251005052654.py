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

# Project Root
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

def load_cleaned_data():
    conn = sqlite3.connect(DB_PATH)
    
    # Sessions
    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors='coerce')
    df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors='coerce')
    df_sessions["app_name"].fillna("Unknown App", inplace=True)
    df_sessions["audio_label"].fillna("N/A", inplace=True)
    df_sessions["intent_label"].fillna("N/A", inplace=True)
    df_sessions["intent_confidence"].fillna(0, inplace=True)
    df_sessions["duration_min"] = (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60

    # Multi-Modal Logs
    df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors='coerce')

    # Memory Decay
    df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
    df_decay["last_seen_ts"] = pd.to_datetime(df_decay["last_seen_ts"], errors='coerce')
    df_decay["updated_at"] = pd.to_datetime(df_decay["updated_at"], errors='coerce')

    conn.close()
    return df_sessions, df_logs, df_decay

df_sessions, df_logs, df_decay = load_cleaned_data()

# -----------------------------
# Streamlit Page Setup
# -----------------------------
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide")
st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Visualize your learning sessions, memory scores, and knowledge graph in one place.")

# -----------------------------
# Sidebar Settings
# -----------------------------
st.sidebar.title("Tracker Settings")

# General toggles
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Graph Visual Settings")

# Node size and edge transparency
node_min_size = st.sidebar.slider("Min Node Size", 100, 500, 200)
node_max_size = st.sidebar.slider("Max Node Size", 500, 2000, 800)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.1, 1.0, 0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("Memory Decay Settings")

# Optional user-controlled decay rate (for experimentation)
user_decay_rate = st.sidebar.slider("User Decay Rate λ", 0.01, 1.0, 0.1)
prediction_hours = st.sidebar.slider("Predict Forgetting For (hours)", 1, 72, 24)


# -----------------------------
# Page Title
# -----------------------------
st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Visualize your learning sessions, memory scores, and knowledge graph in one place.")

# -----------------------------
# Tabs
# -----------------------------
tabs = st.tabs([
    "Overview",
    "Knowledge Graph",
    "Sessions",
    "Memory Decay",
    "Predicted Forgetting"
])

# -----------------------------
# Overview Tab
# -----------------------------
with tabs[0]:
    st.subheader("📊 Dashboard Overview")

    # Connect to DB
    conn = sqlite3.connect(DB_PATH)
    try:
        # Fetch sessions
        df_sessions = pd.read_sql(
            "SELECT start_ts AS start, end_ts AS end, app_name AS app FROM sessions ORDER BY start_ts DESC", conn
        )
        df_sessions["start"] = pd.to_datetime(df_sessions["start"], errors='coerce')
        df_sessions["end"] = pd.to_datetime(df_sessions["end"], errors='coerce')
        df_sessions = df_sessions.dropna()
        df_sessions["duration"] = (df_sessions["end"] - df_sessions["start"]).dt.total_seconds() / 60
        total_hours = df_sessions["duration"].sum() / 60
        avg_session = df_sessions["duration"].mean()
        num_sessions = len(df_sessions)
    except Exception as e:
        st.warning(f"No session data yet: {e}")
        total_hours, avg_session, num_sessions = 0, 0, 0
    finally:
        conn.close()

    # ---- KPI Cards ----
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Hours", f"{total_hours:.2f} h")
    col2.metric("Avg Session", f"{avg_session:.1f} min")
    col3.metric("Number of Sessions", f"{num_sessions}")

    # Mini line chart for daily hours
    if not df_sessions.empty:
        daily_hours = df_sessions.groupby(df_sessions["start"].dt.date)["duration"].sum() / 60
        col4.line_chart(daily_hours, height=100)

    st.markdown("---")

    # ---- Memory Score Cards ----
    st.subheader("🧠 Memory Scores")
    conn = sqlite3.connect(DB_PATH)
    try:
        df_mem = pd.read_sql("SELECT concept, memory_score, next_review_time FROM metrics", conn)
        df_mem["memory_score"] = pd.to_numeric(df_mem["memory_score"], errors='coerce')
    except Exception as e:
        st.warning(f"No memory metrics: {e}")
        df_mem = pd.DataFrame()
    finally:
        conn.close()

    if not df_mem.empty:
        # Table with gradient
        st.dataframe(df_mem.sort_values("memory_score").style.background_gradient(subset=["memory_score"], cmap="viridis"))

        # Top 3 concepts in cards
        top3 = df_mem.sort_values("memory_score", ascending=False).head(3)
        st.subheader("Top Concepts")
        c1, c2, c3 = st.columns(3)
        for idx, col in enumerate([c1, c2, c3]):
            if idx < len(top3):
                concept = top3.iloc[idx]["concept"]
                score = top3.iloc[idx]["memory_score"]
                next_r = top3.iloc[idx]["next_review_time"]
                col.markdown(f"**{concept}**")
                col.metric("Memory Score", f"{score:.2f}")
                col.markdown(f"Next Review: {next_r}")
    else:
        st.info("No memory metrics found yet.")


# -----------------------------
# Knowledge Graph Tab
# -----------------------------
with tabs[1]:
    st.subheader("🕸️ Knowledge Graph")

    # Fetch graph data from metrics table
    conn = sqlite3.connect(DB_PATH)
    try:
        df_mem = pd.read_sql("SELECT concept, memory_score FROM metrics", conn)
        df_mem["memory_score"] = pd.to_numeric(df_mem["memory_score"], errors='coerce')
    except Exception as e:
        st.warning(f"Cannot fetch memory graph data: {e}")
        df_mem = pd.DataFrame()
    finally:
        conn.close()

    if not df_mem.empty:
        # Build a simple NetworkX graph
        G = nx.Graph()
        for _, row in df_mem.iterrows():
            G.add_node(row['concept'], memory_score=row['memory_score'])

        # Example: fully connected for demo (optional, replace with actual edges logic)
        concepts = list(G.nodes)
        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                G.add_edge(concepts[i], concepts[j])

        # Node visualization
        memory_scores = [G.nodes[n]['memory_score'] for n in G.nodes]
        cmap = cm.viridis
        norm = mcolors.Normalize(vmin=0, vmax=1)
        node_colors = [cmap(norm(score)) for score in memory_scores]
        node_sizes = [200 + 1800 * score for score in memory_scores]  # scalable

        fig, ax = plt.subplots(figsize=(12, 10))
        pos = nx.spring_layout(G, seed=42, k=0.8)
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)
        nx.draw_networkx_edges(G, pos, alpha=0.5, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=10, ax=ax)

        # Colorbar
        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        fig.colorbar(sm, ax=ax, label="Memory Score")

        st.pyplot(fig)
    else:
        st.info("Knowledge graph is empty. Add some memory metrics to visualize.")


# -----------------------------
# Sessions Tab
# -----------------------------
with tabs[2]:
    st.subheader("⏱️ Session Timeline & Heatmap")

    conn = sqlite3.connect(DB_PATH)
    try:
        df_sess = pd.read_sql(
            "SELECT start_ts AS start, end_ts AS end, app_name AS app FROM sessions ORDER BY start_ts DESC LIMIT 100",
            conn
        )

        # Convert timestamps
        df_sess["start"] = pd.to_datetime(df_sess["start"], errors='coerce')
        df_sess["end"] = pd.to_datetime(df_sess["end"], errors='coerce')
        df_sess = df_sess.dropna(subset=["start", "end"])

        # Calculate duration in minutes
        df_sess["duration"] = (df_sess["end"] - df_sess["start"]).dt.total_seconds() / 60

        # Timeline chart using Plotly
        fig_tl = px.timeline(
            df_sess, 
            x_start="start", 
            x_end="end", 
            y="app", 
            color="app",
            title="Recent Sessions Timeline"
        )
        fig_tl.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_tl, use_container_width=True)

        # Heatmap: duration per app per day
        heat_df = df_sess.groupby([df_sess["app"], df_sess["start"].dt.date])["duration"].sum().reset_index()
        heat_pivot = heat_df.pivot(index="app", columns="start", values="duration").fillna(0)

        fig_hm = go.Figure(
            data=go.Heatmap(
                z=heat_pivot.values,
                x=[str(d) for d in heat_pivot.columns],
                y=heat_pivot.index,
                colorscale="Viridis",
                hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} min<extra></extra>"
            )
        )
        fig_hm.update_layout(title="App Usage Duration Heatmap")
        st.plotly_chart(fig_hm, use_container_width=True)

    except Exception as e:
        st.warning(f"No session data available: {e}")
    finally:
        conn.close()


