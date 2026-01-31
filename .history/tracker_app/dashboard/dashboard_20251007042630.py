# dashboard/dashboard.py
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

# ----------------------------- #
# Project Root
# ----------------------------- #
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# ----------------------------- #
# Fix font warnings in matplotlib
# ----------------------------- #
plt.rcParams['font.sans-serif'] = ['Arial']

# ----------------------------- #
# Safe DB Loading
# ----------------------------- #
def load_cleaned_data():
    empty_sessions = pd.DataFrame(columns=[
        "start_ts","end_ts","app_name","audio_label","intent_label",
        "intent_confidence","duration_min"
    ])
    empty_logs = pd.DataFrame(columns=["timestamp","ocr_keywords","audio_label","attention_score","interaction_rate","intent_label","intent_confidence","memory_score"])
    empty_decay = pd.DataFrame(columns=["concept","timestamp","memory_score"])
    empty_metrics = pd.DataFrame(columns=["concept","next_review_time","memory_score"])
    
    try:
        conn = sqlite3.connect(DB_PATH)
    except sqlite3.OperationalError as e:
        st.error(f"Database connection failed: {e}")
        return empty_sessions, empty_logs, empty_decay, empty_metrics

    # Sessions
    try:
        df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
        df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors='coerce')
        df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors='coerce')
        df_sessions["app_name"] = df_sessions.get("app_name", "Unknown App").fillna("Unknown App")
        df_sessions["audio_label"] = df_sessions.get("audio_label", "N/A").fillna("N/A")
        df_sessions["intent_label"] = df_sessions.get("intent_label", "N/A").fillna("N/A")
        df_sessions["intent_confidence"] = pd.to_numeric(df_sessions.get("intent_confidence", 0), errors='coerce').fillna(0)
        df_sessions["duration_min"] = ((df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds()/60).fillna(0)
    except Exception:
        df_sessions = empty_sessions

    # Multi-Modal Logs
    try:
        df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
        df_logs["timestamp"] = pd.to_datetime(df_logs.get("timestamp", pd.Series()), errors='coerce')
    except Exception:
        df_logs = empty_logs

    # Memory Decay
    try:
        df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
        df_decay["last_seen_ts"] = pd.to_datetime(df_decay.get("last_seen_ts", pd.Series()), errors='coerce')
        df_decay["updated_at"] = pd.to_datetime(df_decay.get("updated_at", pd.Series()), errors='coerce')
    except Exception:
        df_decay = empty_decay

    # Metrics / Reminders
    try:
        df_metrics = pd.read_sql("SELECT concept, next_review_time, memory_score FROM metrics", conn)
        df_metrics["next_review_time"] = pd.to_datetime(df_metrics.get("next_review_time", pd.Series()), errors='coerce')
        df_metrics["memory_score"] = pd.to_numeric(df_metrics.get("memory_score", 0), errors='coerce').fillna(0)
    except Exception:
        df_metrics = empty_metrics

    conn.close()
    return df_sessions, df_logs, df_decay, df_metrics

df_sessions, df_logs, df_decay, df_metrics = load_cleaned_data()

# ----------------------------- #
# Streamlit Page Setup
# ----------------------------- #
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide")
st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Visualize your learning sessions, memory scores, knowledge graph, upcoming reminders, and more.")

# ----------------------------- #
# Sidebar Settings
# ----------------------------- #
st.sidebar.title("Tracker Settings")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Graph Visual Settings")
node_min_size = st.sidebar.slider("Min Node Size", 100, 500, 200)
node_max_size = st.sidebar.slider("Max Node Size", 500, 2000, 800)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.1, 1.0, 0.5)

# ----------------------------- #
# Tabs
# ----------------------------- #
tabs = st.tabs([
    "Overview", "Knowledge Graph", "Sessions",
    "Memory Decay", "Predicted Forgetting",
    "Multi-Modal Logs", "Upcoming Reminders"
])

# ----------------------------- #
# Overview Tab
# ----------------------------- #
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
        col4.line_chart(daily_hours.fillna(0), height=100)

    st.markdown("---")

    # Memory Scores
    st.subheader("🧠 Memory Scores")
    try:
        sync_db_to_graph()
        G = get_graph()
    except Exception:
        G = nx.Graph()

    if G and G.nodes:
        mem_table = []
        for node in G.nodes:
            mem_score = np.nan_to_num(G.nodes[node].get("memory_score", 0.3))
            next_review = G.nodes[node].get("next_review_time", "N/A")
            mem_table.append({"Concept": node, "Memory Score": round(mem_score,2), "Next Review": next_review})

        df_mem = pd.DataFrame(mem_table).sort_values("Memory Score")
        st.dataframe(df_mem.style.background_gradient(subset=["Memory Score"], cmap="viridis"))

        # Top concepts
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

# ----------------------------- #
# Knowledge Graph Tab
# ----------------------------- #
with tabs[1]:
    st.subheader("🕸️ Knowledge Graph")
    if G and G.nodes:
        memory_scores = [np.nan_to_num(G.nodes[n].get('memory_score',0.3)) for n in G.nodes]
        cmap = cm.viridis
        norm = mcolors.Normalize(vmin=0, vmax=1)
        node_colors = [cmap(norm(score)) for score in memory_scores]
        node_sizes = [node_min_size + (node_max_size - node_min_size) * score for score in memory_scores]

        fig, ax = plt.subplots(figsize=(12,10))
        try:
            pos = nx.spring_layout(G, seed=42, k=0.8)
            nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)
            nx.draw_networkx_edges(G, pos, alpha=edge_alpha, ax=ax)
            nx.draw_networkx_labels(G, pos, font_size=10, ax=ax)
            sm = cm.ScalarMappable(cmap=cmap, norm=norm)
            sm.set_array([])
            fig.colorbar(sm, ax=ax, label="Memory Score")
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Failed to render knowledge graph: {e}")
    else:
        st.info("Knowledge graph empty.")

# ----------------------------- #
# Sessions Tab
# ----------------------------- #
with tabs[2]:
    st.subheader("⏱️ Session Timeline & Heatmap")
    if not df_sessions_filtered.empty:
        df_sess = df_sessions_filtered.copy()
        df_sess["end_ts"] = df_sess["end_ts"].where(df_sess["end_ts"] > df_sess["start_ts"], df_sess["start_ts"] + pd.Timedelta(seconds=5))
        df_sess["duration"] = (df_sess["end_ts"] - df_sess["start_ts"]).dt.total_seconds()/60

        try:
            fig_tl = px.timeline(df_sess, x_start="start_ts", x_end="end_ts", y="app_name", color="app_name")
            fig_tl.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_tl, use_container_width=True)
        except Exception as e:
            st.error(f"Timeline plot failed: {e}")

        try:
            heat_df = df_sess.groupby(["app_name", df_sess["start_ts"].dt.date])["duration"].sum().reset_index()
            heat_pivot = heat_df.pivot(index="app_name", columns="start_ts", values="duration").fillna(0)
            if not heat_pivot.empty:
                fig_hm = go.Figure(data=go.Heatmap(
                    z=heat_pivot.values,
                    x=[str(d) for d in heat_pivot.columns],
                    y=heat_pivot.index,
                    colorscale="Viridis",
                    hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} min<extra></extra>"
                ))
                fig_hm.update_layout(title="App Usage Duration Heatmap")
                st.plotly_chart(fig_hm, use_container_width=True)
        except Exception as e:
            st.error(f"Heatmap failed: {e}")


