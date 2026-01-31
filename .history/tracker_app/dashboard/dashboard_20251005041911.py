# dashboard/dashboard.py
import sys
import os
import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import sqlite3
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------
# Project Paths
# -----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"  # Adjust your path
sys.path.append(PROJECT_ROOT)

from core.knowledge_graph import get_graph, sync_db_to_graph
from config import DB_PATH

# -----------------------------
# Sidebar Settings
# -----------------------------
st.sidebar.title("Settings")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Graph Design Settings:**")
node_min_size = st.sidebar.slider("Min Node Size", 100, 500, 200)
node_max_size = st.sidebar.slider("Max Node Size", 500, 2000, 800)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.1, 1.0, 0.5)

# -----------------------------
# Page Title
# -----------------------------
st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Visualize your learning sessions, memory scores, and knowledge graph in real-time.")

# -----------------------------
# Quick Stats
# -----------------------------
st.subheader("⚡ Quick Stats")
conn = sqlite3.connect(DB_PATH)

# Total app usage (minutes)
df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
total_minutes = ((pd.to_datetime(df_sessions['end_ts']) - pd.to_datetime(df_sessions['start_ts'])).dt.total_seconds() / 60).sum() if not df_sessions.empty else 0

# Total OCR keywords
df_ocr = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
total_keywords = sum([len(eval(row)) if row else 0 for row in df_ocr['ocr_keywords']]) if not df_ocr.empty else 0

# Latest audio label & focus
latest_audio = df_ocr['audio_label'].iloc[-1] if not df_ocr.empty else "N/A"
latest_focus = df_ocr['attention_score'].iloc[-1] if not df_ocr.empty else 0

conn.close()

col1, col2, col3, col4 = st.columns(4)
col1.metric("App Usage", f"{total_minutes/60:.2f} hrs")
col2.metric("Keywords Detected", total_keywords)
col3.metric("Latest Audio", latest_audio)
col4.metric("Focus Level", latest_focus)

# -----------------------------
# Sync Knowledge Graph
# -----------------------------
sync_db_to_graph()
G = get_graph()

# -----------------------------
# Memory Scores Table
# -----------------------------
st.subheader("📊 Memory Scores Overview")
if len(G.nodes) == 0:
    st.warning("Knowledge graph is empty. Run the tracker first!")
else:
    mem_data = []
    for node in G.nodes:
        mem_score = G.nodes[node].get('memory_score', 0.0)
        next_review = G.nodes[node].get('next_review_time', "N/A")
        mem_data.append({
            "Concept": node,
            "Memory Score": mem_score,
            "Next Review": next_review
        })

    mem_df = pd.DataFrame(mem_data)
    st.dataframe(mem_df.style.bar(subset=['Memory Score'], color='#7c4dff').format({"Memory Score": "{:.2f}"}), height=400)

# -----------------------------
# Knowledge Graph Visualization
# -----------------------------
st.subheader("🕸️ Knowledge Graph")
if len(G.nodes) > 0:
    memory_scores = [G.nodes[n].get('memory_score', 0.3) for n in G.nodes]
    cmap = cm.viridis
    norm = mcolors.Normalize(vmin=0, vmax=1)
    node_colors = [cmap(norm(score)) for score in memory_scores]
    node_sizes = [node_min_size + (node_max_size - node_min_size) * score for score in memory_scores]

    fig, ax = plt.subplots(figsize=(12, 10))
    pos = nx.spring_layout(G, seed=42, k=0.8)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)
    nx.draw_networkx_edges(G, pos, alpha=edge_alpha, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=10, ax=ax)
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, label="Memory Score")
    st.pyplot(fig)

# -----------------------------
# Session Timeline
# -----------------------------
st.subheader("⏱️ Session Timeline")
try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT start_ts, end_ts, app_name FROM sessions ORDER BY start_ts DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()

    if rows:
        session_df = pd.DataFrame(rows, columns=["Start", "End", "App"])
        session_df["Start"] = pd.to_datetime(session_df["Start"], errors='coerce')
        session_df["End"] = pd.to_datetime(session_df["End"], errors='coerce')
        session_df["End"] = session_df["End"].where(session_df["End"] > session_df["Start"], session_df["Start"] + pd.Timedelta(seconds=5))

        # Timeline plot
        fig2 = px.timeline(
            session_df,
            x_start="Start",
            x_end="End",
            y="App",
            color="App",
            hover_data=["Start", "End"],
            title="Recent Activity Timeline"
        )
        fig2.update_yaxes(autorange="reversed")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("No session data found. Run the tracker first!")

except sqlite3.OperationalError as e:
    st.error(f"Database error: {e}")

# -----------------------------
# Memory Decay Curves
# -----------------------------
st.subheader("📉 Memory Decay Curves")

def fetch_memory_decay(concept=None):
    conn = sqlite3.connect(DB_PATH)
    if concept:
        query = """
            SELECT keyword AS concept, last_seen_ts AS timestamp, predicted_recall AS memory_score
            FROM memory_decay
            WHERE keyword = ?
            ORDER BY last_seen_ts ASC
        """
        df = pd.read_sql(query, conn, params=(concept,))
    else:
        query = """
            SELECT keyword AS concept, last_seen_ts AS timestamp, predicted_recall AS memory_score
            FROM memory_decay
            ORDER BY last_seen_ts ASC
        """
        df = pd.read_sql(query, conn)
    conn.close()
    return df

# Overall decay
df_decay = fetch_memory_decay()
if not df_decay.empty:
    df_decay["timestamp"] = pd.to_datetime(df_decay["timestamp"], errors='coerce')
    df_decay["memory_score"] = pd.to_numeric(df_decay["memory_score"], errors='coerce')

    fig_decay = px.line(
        df_decay,
        x="timestamp",
        y="memory_score",
        color="concept",
        markers=True,
        title="Forgetting Curve / Memory Decay per Concept",
        labels={"timestamp": "Time", "memory_score": "Predicted Recall"}
    )
    fig_decay.update_layout(yaxis=dict(range=[0, 1]), legend_title_text="Concept")
    st.plotly_chart(fig_decay, use_container_width=True)
else:
    st.warning("No memory decay data found yet. Run the tracker first!")

# Individual Concept Decay
st.subheader("🧠 Individual Concept Decay Viewer")
concepts = list(G.nodes)
selected_concepts = st.multiselect("Select concepts", concepts, default=concepts[:3])
if selected_concepts:
    fig_indiv = go.Figure()
    for concept in selected_concepts:
        df_concept = fetch_memory_decay(concept)
        if not df_concept.empty:
            df_concept["timestamp"] = pd.to_datetime(df_concept["timestamp"], errors='coerce')
            df_concept["memory_score"] = pd.to_numeric(df_concept["memory_score"], errors='coerce')
            fig_indiv.add_trace(go.Scatter(
                x=df_concept['timestamp'],
                y=df_concept['memory_score'],
                mode='lines+markers',
                name=concept
            ))
    fig_indiv.update_layout(
        title="Memory Decay Over Time (Selected Concepts)",
        xaxis_title="Time",
        yaxis_title="Memory Score",
        yaxis=dict(range=[0, 1])
    )
    st.plotly_chart(fig_indiv, use_container_width=True)

# Predicted Forgetting Curve
st.subheader("📈 Predicted Forgetting Curve Overlay")
concept = st.selectbox("Choose concept for prediction", concepts)
if concept:
    times = np.linspace(0, 24, 50)
    scores = np.exp(-0.1 * times)
    fig_pred = go.Figure()
    fig_pred.add_trace(go.Scatter(
        x=[datetime.now() + timedelta(hours=t) for t in times],
        y=scores,
        mode='lines',
        name=f"Predicted {concept}"
    ))
    fig_pred.update_layout(
        title=f"Predicted Forgetting Curve for {concept}",
        xaxis_title="Time",
        yaxis_title="Predicted Recall",
        yaxis=dict(range=[0, 1])
    )
    st.plotly_chart(fig_pred, use_container_width=True)
