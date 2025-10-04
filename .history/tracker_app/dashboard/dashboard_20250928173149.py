# -----------------------------
# Enhanced FKT Dashboard v2
# -----------------------------
import sys, os, io
import pandas as pd
import streamlit as st
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from datetime import datetime, timedelta
from core.knowledge_graph import get_graph, sync_db_to_graph
from config import DB_PATH

# -----------------------------
# Project Path
# -----------------------------


# -----------------------------
# Sidebar Settings
# -----------------------------
st.sidebar.title("Settings")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Graph Settings:**")
node_min_size = st.sidebar.slider("Min Node Size", 100, 500, 200)
node_max_size = st.sidebar.slider("Max Node Size", 500, 2000, 800)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.1, 1.0, 0.5)
min_mem_score = st.sidebar.slider("Min Memory Score Filter", 0.0, 1.0, 0.0)

# -----------------------------
# Page Title
# -----------------------------
st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Visualize learning sessions, memory scores, and knowledge graph in real-time.")

# -----------------------------
# Sync Knowledge Graph
# -----------------------------
with st.spinner("Syncing knowledge graph..."):
    sync_db_to_graph()
    G = get_graph()

# -----------------------------
# Quick Stats
# -----------------------------
st.subheader("📊 Quick Stats")
total_concepts = len(G.nodes)
avg_memory = sum([G.nodes[n].get('memory_score',0.0) for n in G.nodes])/max(total_concepts,1)

try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT SUM((julianday(end_ts) - julianday(start_ts))*24) FROM sessions")
    total_hours = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM ocr_logs")
    total_keywords = c.fetchone()[0] or 0
    conn.close()
except:
    total_hours = 0
    total_keywords = 0

cols = st.columns(4)
cols[0].metric("Total App Usage", f"{total_hours:.1f} hrs")
cols[1].metric("Tracked Concepts", total_concepts)
cols[2].metric("Avg Memory Score", f"{avg_memory:.2f}")
cols[3].metric("Total OCR Keywords", total_keywords)

# -----------------------------
# Knowledge Graph Section
# -----------------------------
st.subheader("🕸️ Knowledge Graph")
filtered_nodes = [n for n in G.nodes if G.nodes[n].get('memory_score',0) >= min_mem_score]
if not filtered_nodes:
    st.warning("No nodes match the memory score filter.")
else:
    subG = G.subgraph(filtered_nodes)
    node_sizes = [
        node_min_size + (node_max_size-node_min_size)*G.nodes[n].get('memory_score',0)
        for n in subG.nodes
    ]
    memory_scores = [subG.nodes[n].get('memory_score',0) for n in subG.nodes]
    node_colors = px.colors.sequential.Viridis

    fig = go.Figure()

    pos = nx.spring_layout(subG, seed=42, k=0.8)
    for n in subG.nodes:
        fig.add_trace(go.Scatter(
            x=[pos[n][0]], y=[pos[n][1]],
            text=f"{n}<br>Memory: {subG.nodes[n].get('memory_score',0):.2f}<br>Next Review: {subG.nodes[n].get('next_review_time','N/A')}",
            mode="markers+text",
            marker=dict(
                size=node_min_size + (node_max_size-node_min_size)*subG.nodes[n].get('memory_score',0),
                color=subG.nodes[n].get('memory_score',0),
                colorscale='Viridis',
                showscale=True
            ),
            textposition="top center",
            hoverinfo="text"
        ))

    for u,v in subG.edges:
        fig.add_trace(go.Scatter(
            x=[pos[u][0], pos[v][0]],
            y=[pos[u][1], pos[v][1]],
            mode="lines",
            line=dict(width=1, color='rgba(100,100,100,0.5)')
        ))

    fig.update_layout(showlegend=False, title="Knowledge Graph", xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig, use_container_width=True)

    # Download Graph Data
    csv_buffer = io.StringIO()
    pd.DataFrame([
        {"Concept": n, "Memory Score": subG.nodes[n].get('memory_score',0), "Next Review": subG.nodes[n].get('next_review_time','N/A')}
        for n in subG.nodes
    ]).to_csv(csv_buffer, index=False)
    st.download_button("Download Graph Data CSV", csv_buffer.getvalue(), "knowledge_graph.csv", "text/csv")

# -----------------------------
# Session Timeline & Heatmap
# -----------------------------
st.subheader("⏱️ Session Timeline & Heatmap")
try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT start_ts, end_ts, app_name FROM sessions ORDER BY start_ts DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()

    if rows:
        session_df = pd.DataFrame(rows, columns=["Start","End","App"])
        session_df["Start"] = pd.to_datetime(session_df["Start"], errors='coerce')
        session_df["End"] = pd.to_datetime(session_df["End"], errors='coerce')
        session_df = session_df.dropna(subset=["Start","End"])
        session_df["Duration_min"] = (session_df["End"] - session_df["Start"]).dt.total_seconds()/60

        # Timeline
        timeline_fig = px.timeline(session_df, x_start="Start", x_end="End", y="App", color="App", hover_data=["Duration_min"])
        timeline_fig.update_yaxes(autorange="reversed")
        st.plotly_chart(timeline_fig, use_container_width=True)

        # Heatmap
        heatmap_df = session_df.groupby([session_df["App"], session_df["Start"].dt.date])["Duration_min"].sum().reset_index()
        heatmap_pivot = heatmap_df.pivot(index="App", columns="Start", values="Duration_min").fillna(0)
        heatmap_fig = go.Figure(go.Heatmap(
            z=heatmap_pivot.values,
            x=[str(d) for d in heatmap_pivot.columns],
            y=heatmap_pivot.index,
            colorscale="Viridis",
            hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} mins<extra></extra>"
        ))
        heatmap_fig.update_layout(title="App Usage Heatmap (Minutes)", xaxis_title="Date", yaxis_title="App")
        st.plotly_chart(heatmap_fig, use_container_width=True)

        # Download Session Data
        csv_buffer2 = io.StringIO()
        session_df.to_csv(csv_buffer2, index=False)
        st.download_button("Download Session Data CSV", csv_buffer2.getvalue(), "session_data.csv", "text/csv")

except sqlite3.OperationalError as e:
    st.error(f"Database error: {e}")
