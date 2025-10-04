# -----------------------------
# Fully Enhanced FKT Dashboard v4
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
# Project Path Fix for 'core'
# -----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

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
st.markdown("Visualize your learning sessions, memory scores, and knowledge graph in real-time.")

# -----------------------------
# Sync Knowledge Graph
# -----------------------------
with st.spinner("Syncing knowledge graph..."):
    try:
        sync_db_to_graph()
        G = get_graph()
    except Exception as e:
        st.error(f"Error syncing knowledge graph: {e}")
        G = nx.Graph()  # fallback empty graph

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
except Exception:
    total_hours = 0
    total_keywords = 0

cols = st.columns(4)
cols[0].metric("Total App Usage", f"{total_hours:.1f} hrs")
cols[1].metric("Tracked Concepts", total_concepts)
cols[2].metric("Avg Memory Score", f"{avg_memory:.2f}")
cols[3].metric("Total OCR Keywords", total_keywords)

# -----------------------------
# Knowledge Graph
# -----------------------------
st.subheader("🕸️ Knowledge Graph")
filtered_nodes = [n for n in G.nodes if G.nodes[n].get('memory_score',0) >= min_mem_score]
if not filtered_nodes:
    st.warning("No nodes match the memory score filter. Displaying all nodes as fallback.")
    filtered_nodes = list(G.nodes)

if filtered_nodes:
    subG = G.subgraph(filtered_nodes)
    pos = nx.spring_layout(subG, seed=42, k=0.8)
    fig = go.Figure()

    for n in subG.nodes:
        mem_score = subG.nodes[n].get('memory_score', 0.3)
        fig.add_trace(go.Scatter(
            x=[pos[n][0]], y=[pos[n][1]],
            text=f"{n}<br>Memory: {mem_score:.2f}<br>Next Review: {subG.nodes[n].get('next_review_time','N/A')}",
            mode="markers+text",
            marker=dict(
                size=node_min_size + (node_max_size-node_min_size)*mem_score,
                color=mem_score,
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
            line=dict(width=1, color=f"rgba(0,0,0,{edge_alpha})")
        ))

    fig.update_layout(showlegend=False, title="Knowledge Graph", xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    st.plotly_chart(fig, use_container_width=True)

    # Download Graph CSV
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

    if not rows:
        st.warning("No session data found. Using fallback demo data.")
        rows = [
            (datetime.now()-timedelta(minutes=30), datetime.now(), "Demo App"),
            (datetime.now()-timedelta(minutes=60), datetime.now()-timedelta(minutes=30), "Demo App 2")
        ]

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

except Exception as e:
    st.error(f"Session timeline error: {e}")

# -----------------------------
# Learning Analytics Charts
# -----------------------------
st.subheader("📈 Learning Analytics")

# -----------------------------
# Focus & Retention
# -----------------------------
try:
    # Replace with real DB queries
    hours = list(range(24))
    focus_scores = [0.5 + 0.5*abs((i-12)/12) for i in hours]
    retention_scores = [90 - i*2 for i in hours]
except:
    hours = list(range(24))
    focus_scores = [0.5]*24
    retention_scores = [50]*24

fig_focus = px.line(x=hours, y=focus_scores, labels={"x":"Hour","y":"Focus Score"}, title="Focus Trend")
fig_retention = px.line(x=hours, y=retention_scores, labels={"x":"Hour","y":"Retention %"}, title="Retention Trend")
st.plotly_chart(fig_focus, use_container_width=True)
st.plotly_chart(fig_retention, use_container_width=True)

# -----------------------------
# Memory Analytics & Topic Retention
# -----------------------------
try:
    topics = ["Math","Physics","Chemistry","OCR"]
    reviewed = [5,3,4,2]
    forgotten = [1,2,1,3]
    topic_retention = [90,70,85,60]
except:
    topics = ["Demo"]
    reviewed = [1]
    forgotten = [0]
    topic_retention = [50]

# Memory Analytics
fig_memory = go.Figure()
fig_memory.add_trace(go.Bar(x=topics, y=reviewed, name="Reviewed", marker_color='green'))
fig_memory.add_trace(go.Bar(x=topics, y=forgotten, name="Forgotten", marker_color='red'))
fig_memory.update_layout(barmode='group', title="Memory Analytics per Topic")
st.plotly_chart(fig_memory, use_container_width=True)

# Topic Retention
fig_topic_retention = px.line(x=topics, y=topic_retention, labels={"x":"Topic","y":"Retention %"}, title="Topic Retention")
st.plotly_chart(fig_topic_retention, use_container_width=True)

# -----------------------------
# Keyword Analytics
# -----------------------------
try:
    keywords = ["Force","Energy","Velocity","OCR"]
    freq = [10,7,5,12]
    trend = [2,5,3,7]
except:
    keywords = ["Demo"]
    freq = [1]
    trend = [1]

fig_keywords = go.Figure()
fig_keywords.add_trace(go.Bar(x=keywords, y=freq, name="Frequency", marker_color='#36a2eb'))
fig_keywords.add_trace(go.Scatter(x=keywords, y=trend, name="Trend", marker_color='#9c27b0'))
fig_keywords.update_layout(title="Top OCR Keywords & Trends")
st.plotly_chart(fig_keywords, use_container_width=True)
