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
# Page Title
# -----------------------------
st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Visualize your learning sessions, memory scores, and knowledge graph in one place.")

# -----------------------------
# Tabs
# -----------------------------
tabs = st.tabs(["Overview", "Knowledge Graph", "Sessions", "Memory Decay", "Predicted Forgetting"])

# -----------------------------
# Overview Tab
# -----------------------------
with tabs[0]:
    st.subheader("📊 Dashboard Overview")

    # Connect to DB
    conn = sqlite3.connect(DB_PATH)
    try:
        df_sessions = pd.read_sql("SELECT start_ts AS start, end_ts AS end, app_name AS app FROM sessions ORDER BY start_ts DESC", conn)
        df_sessions["start"] = pd.to_datetime(df_sessions["start"], errors='coerce')
        df_sessions["end"] = pd.to_datetime(df_sessions["end"], errors='coerce')
        df_sessions = df_sessions.dropna()
        df_sessions["duration"] = (df_sessions["end"] - df_sessions["start"]).dt.total_seconds() / 60
        total_hours = df_sessions["duration"].sum() / 60
        avg_session = df_sessions["duration"].mean()
        num_sessions = len(df_sessions)
        conn.close()
    except Exception as e:
        st.warning(f"No session data yet: {e}")
        total_hours, avg_session, num_sessions = 0, 0, 0

    # ---- KPI Cards ----
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Hours", f"{total_hours:.2f} h")
    col2.metric("Avg Session", f"{avg_session:.1f} min")
    col3.metric("Number of Sessions", f"{num_sessions}")
    
    # Small mini-graph: Hours per day
    if not df_sessions.empty:
        daily_hours = df_sessions.groupby(df_sessions["start"].dt.date)["duration"].sum() / 60
        col4.line_chart(daily_hours, height=100)

    st.markdown("---")

    # ---- Memory Score Cards ----
    st.subheader("🧠 Memory Scores")
    sync_db_to_graph()
    G = get_graph()
    
    if G.nodes:
        mem_table = []
        for node in G.nodes:
            mem_score = G.nodes[node].get("memory_score", 0.3)
            next_review = G.nodes[node].get("next_review_time", "N/A")
            mem_table.append({"Concept": node, "Memory Score": round(mem_score,2), "Next Review": next_review})

        df_mem = pd.DataFrame(mem_table).sort_values("Memory Score")
        # Designer table with gradient
        st.dataframe(df_mem.style.background_gradient(subset=["Memory Score"], cmap="viridis"))
        
        # Top 3 concepts in cards
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
# Sessions Tab
# -----------------------------
with tabs[2]:
    st.subheader("⏱️ Session Timeline & Heatmap")
    conn = sqlite3.connect(DB_PATH)
    try:
        df_sess = pd.read_sql("SELECT start_ts AS start, end_ts AS end, app_name AS app FROM sessions ORDER BY start_ts DESC LIMIT 50", conn)
        df_sess["start"] = pd.to_datetime(df_sess["start"], errors='coerce')
        df_sess["end"] = pd.to_datetime(df_sess["end"], errors='coerce')
        df_sess = df_sess.dropna()
        df_sess["end"] = df_sess["end"].where(df_sess["end"] > df_sess["start"], df_sess["start"] + pd.Timedelta(seconds=5))
        df_sess["duration"] = (df_sess["end"] - df_sess["start"]).dt.total_seconds()/60

        # Timeline
        fig_tl = px.timeline(df_sess, x_start="start", x_end="end", y="app", color="app")
        fig_tl.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_tl, width="stretch")

        # Heatmap
        heat_df = df_sess.groupby(["app", df_sess["start"].dt.date])["duration"].sum().reset_index()
        heat_pivot = heat_df.pivot(index="app", columns="start", values="duration").fillna(0)
        fig_hm = go.Figure(data=go.Heatmap(
            z=heat_pivot.values,
            x=[str(d) for d in heat_pivot.columns],
            y=heat_pivot.index,
            colorscale="Viridis",
            hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} min<extra></extra>"
        ))
        fig_hm.update_layout(title="App Usage Duration Heatmap")
        st.plotly_chart(fig_hm, width="stretch")
    except Exception as e:
        st.warning(f"No session data: {e}")
    conn.close()

# -----------------------------
# Memory Decay Tab
# -----------------------------
with tabs[3]:
    st.subheader("📉 Memory Decay Curves")
    def fetch_decay(concept=None):
        conn = sqlite3.connect(DB_PATH)
        if concept:
            df = pd.read_sql("SELECT keyword AS concept, last_seen_ts AS timestamp, predicted_recall AS memory_score FROM memory_decay WHERE keyword = ? ORDER BY last_seen_ts ASC", conn, params=(concept,))
        else:
            df = pd.read_sql("SELECT keyword AS concept, last_seen_ts AS timestamp, predicted_recall AS memory_score FROM memory_decay ORDER BY last_seen_ts ASC", conn)
        conn.close()
        return df

    df_decay = fetch_decay()
    if not df_decay.empty:
        df_decay["timestamp"] = pd.to_datetime(df_decay["timestamp"], errors="coerce")
        df_decay["memory_score"] = pd.to_numeric(df_decay["memory_score"], errors="coerce")
        fig_decay = px.line(df_decay, x="timestamp", y="memory_score", color="concept", markers=True, title="Memory Decay Per Concept", labels={"timestamp":"Time","memory_score":"Recall"})
        fig_decay.update_layout(yaxis=dict(range=[0,1]))
        st.plotly_chart(fig_decay, width="stretch")

    # Individual decay
    st.subheader("🧠 Individual Concept Viewer")
    concepts = list(G.nodes)
    selected = st.multiselect("Select concepts", concepts, default=concepts[:3])
    if selected:
        fig_ind = go.Figure()
        for c in selected:
            df_c = fetch_decay(c)
            if not df_c.empty:
                df_c["timestamp"] = pd.to_datetime(df_c["timestamp"], errors="coerce")
                df_c["memory_score"] = pd.to_numeric(df_c["memory_score"], errors="coerce")
                fig_ind.add_trace(go.Scatter(x=df_c["timestamp"], y=df_c["memory_score"], mode="lines+markers", name=c))
        fig_ind.update_layout(title="Individual Memory Decay", yaxis=dict(range=[0,1]), xaxis_title="Time", yaxis_title="Memory Score")
        st.plotly_chart(fig_ind, width="stretch")

# -----------------------------
# Predicted Forgetting Tab
# -----------------------------
with tabs[4]:
    st.subheader("📈 Predicted Forgetting Overlay")
    selected_pred = st.selectbox("Choose concept", concepts)
    lambda_val = st.slider("Decay rate λ", 0.01, 1.0, 0.1)
    hours = st.slider("Predict for hours", 1, 72, 24)
    if selected_pred:
        times = np.linspace(0, hours, 50)
        scores = np.exp(-lambda_val * times)
        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=[datetime.now() + timedelta(hours=t) for t in times],
            y=scores,
            mode="lines",
            name="Predicted Recall"
        ))
        fig_pred.update_layout(yaxis=dict(range=[0,1]), xaxis_title="Time", yaxis_title="Memory Score", title=f"Predicted Forgetting Curve for {selected_pred}")
        st.plotly_chart(fig_pred, width="stretch")
