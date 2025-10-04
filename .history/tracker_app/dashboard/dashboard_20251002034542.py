dashb
import sys
import os
import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import sqlite3
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# Set project paths
# -----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"  # adjust to your path
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
# Sync Knowledge Graph
# -----------------------------
sync_db_to_graph()
G = get_graph()

# -----------------------------
# Knowledge Graph Section
# -----------------------------
st.subheader("📚 Knowledge Graph Concepts")
if len(G.nodes) == 0:
    st.warning("Knowledge graph is empty. Run the tracker first!")
else:
    # Table of concepts
    table_data = []
    for node in G.nodes:
        mem_score = G.nodes[node].get('memory_score', 0.3)
        next_review = G.nodes[node].get('next_review_time', "N/A")
        table_data.append({
            "Concept": node,
            "Memory Score": round(mem_score, 2),
            "Next Review": next_review
        })
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)

    # Knowledge Graph Visualization
    st.subheader("🕸️ Knowledge Graph Visualization")
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

    # Memory Scores Progress Bars
    st.subheader("📊 Memory Scores Overview")
    for node in G.nodes:
        mem_score = G.nodes[node].get('memory_score', 0.3)
        st.markdown(f"**{node}:** {mem_score:.2f}")
        st.progress(mem_score)

# -----------------------------
# Session Timeline Section
# -----------------------------
st.subheader("⏱️ Session Timeline")
try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT start_ts, end_ts, app_name FROM sessions ORDER BY start_ts DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()

    if len(rows) == 0:
        st.warning("No session data found. Run the tracker first!")
    else:
        session_df = pd.DataFrame(rows, columns=["Start", "End", "App"])
        session_df["Start"] = pd.to_datetime(session_df["Start"], errors='coerce')
        session_df["End"] = pd.to_datetime(session_df["End"], errors='coerce')
        session_df = session_df.dropna(subset=["Start", "End"])

        # Ensure minimum visible duration
        min_duration = pd.Timedelta(seconds=5)
        session_df["End"] = session_df["End"].where(
            session_df["End"] > session_df["Start"],
            session_df["Start"] + min_duration
        )

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
        st.plotly_chart(fig2, width="stretch")

        # -----------------------------
        # Heatmap: App Usage Duration (numeric minutes)
        # -----------------------------
        st.subheader("🔥 App Usage Heatmap")
        session_df["Duration"] = (session_df["End"] - session_df["Start"]).dt.total_seconds() / 60  # minutes
        heatmap_df = session_df.groupby(["App", session_df["Start"].dt.date])["Duration"].sum().reset_index()
        heatmap_pivot = heatmap_df.pivot(index="App", columns="Start", values="Duration").fillna(0)

        fig3 = go.Figure(
            data=go.Heatmap(
                z=heatmap_pivot.values,
                x=[str(d) for d in heatmap_pivot.columns],
                y=heatmap_pivot.index,
                colorscale="Viridis",
                hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} mins<extra></extra>"
            )
        )
        fig3.update_layout(
            title="App Usage Duration Heatmap (Minutes)",
            xaxis_title="Date",
            yaxis_title="App"
        )
        st.plotly_chart(fig3, width="stretch")

except sqlite3.OperationalError as e:
    st.error(f"Database error: {e}")

# -----------------------------
# Optional: Auto Refresh
# -----------------------------
# st.experimental_rerun()
