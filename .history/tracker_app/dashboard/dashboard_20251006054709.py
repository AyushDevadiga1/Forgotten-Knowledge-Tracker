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
    df_metrics = pd.read_sql("SELECT concept, next_review_time, memory_score FROM metrics", conn)
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
    "Overview", "Knowledge Graph", "Sessions",
    "Memory Decay", "Predicted Forgetting",
    "Multi-Modal Logs", "Upcoming Reminders"
])

# -----------------------------
# Sync Knowledge Graph
# -----------------------------
sync_db_to_graph()
G = get_graph()
concepts = list(G.nodes)

# -----------------------------
# Overview Tab
# -----------------------------
with tabs[0]:
    st.subheader("📊 Dashboard Overview")
    
    # KPI Cards
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

    st.markdown("---")

    # Memory Scores Table
    st.subheader("🧠 Memory Scores")
    if G.nodes:
        mem_table = []
        for n in G.nodes:
            mem_score = G.nodes[n].get("memory_score", 0.3)
            if mem_score is None or np.isnan(mem_score):
                mem_score = 0.3
            next_review = G.nodes[n].get("next_review_time", "N/A")
            intent_conf = G.nodes[n].get("intent_conf", 1.0)
            mem_table.append({
                "Concept": n,
                "Memory Score": round(mem_score,2),
                "Next Review": next_review,
                "Intent Conf": round(intent_conf,2)
            })
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
    st.subheader("🕸️ Knowledge Graph (Interactive)")
    if G.nodes:
        mem_scores = [G.nodes[n].get("memory_score", 0.3) if G.nodes[n].get("memory_score") is not None else 0.3 for n in G.nodes]
        labels = list(G.nodes)

        pos = nx.spring_layout(G, seed=42, k=0.8) if len(G.nodes) > 1 else {n: (0,0) for n in G.nodes}
        node_x, node_y = [pos[n][0] for n in G.nodes], [pos[n][1] for n in G.nodes]

        # Edge coordinates
        edge_x, edge_y = [], []
        for e in G.edges:
            x0, y0 = pos[e[0]]
            x1, y1 = pos[e[1]]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=labels,
            hovertext=[f"{n}<br>Memory: {ms:.2f}<br>Next: {G.nodes[n].get('next_review_time','N/A')}" 
                       for n, ms in zip(labels, mem_scores)],
            marker=dict(
                size=[node_min_size + ms*(node_max_size-node_min_size) for ms in mem_scores],
                color=mem_scores,
                colorscale='Viridis',
                cmin=0, cmax=1,
                showscale=True
            ),
            textposition="top center"
        )

        fig = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(showlegend=False, hovermode='closest'))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Knowledge graph empty.")

# -----------------------------
# Sessions Tab
# -----------------------------
with tabs[2]:
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
with tabs[3]:
    st.subheader("📉 Memory Decay Curves")
    def fetch_decay(concept=None):
        conn = sqlite3.connect(DB_PATH)
        if concept:
            df = pd.read_sql(
                "SELECT keyword AS concept, last_seen_ts AS timestamp, predicted_recall AS memory_score FROM memory_decay WHERE keyword = ? ORDER BY last_seen_ts ASC",
                conn, params=(concept,)
            )
        else:
            df = pd.read_sql(
                "SELECT keyword AS concept, last_seen_ts AS timestamp, predicted_recall AS memory_score FROM memory_decay ORDER BY last_seen_ts ASC",
                conn
            )
        conn.close()
        return df

    df_decay = fetch_decay()
    if not df_decay.empty:
        df_decay["timestamp"] = pd.to_datetime(df_decay["timestamp"], errors="coerce")
        df_decay["memory_score"] = pd.to_numeric(df_decay["memory_score"], errors="coerce")
        fig_decay = px.line(df_decay, x="timestamp", y="memory_score", color="concept", markers=True,
                            title="Memory Decay Per Concept", labels={"timestamp":"Time","memory_score":"Recall"})
        fig_decay.update_layout(yaxis=dict(range=[0,1]))
        st.plotly_chart(fig_decay, use_container_width=True)

    st.subheader("🧠 Individual Concept Viewer")
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
        st.plotly_chart(fig_ind, use_container_width=True)

# -----------------------------
# Predicted Forgetting Tab
# -----------------------------
with tabs[4]:
    st.subheader("📈 Predicted Forgetting Overlay")
    if concepts:
        selected_pred = st.selectbox("Choose concept", concepts)
        lambda_val = 0.1
        hours = 24
        if selected_pred:
            df_last = fetch_decay(selected_pred)
            last_score = df_last["memory_score"].iloc[-1] if not df_last.empty else 0.5
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

# -----------------------------
# Multi-Modal Logs Tab
# -----------------------------
with tabs[5]:
    st.subheader("🎤 Multi-Modal Logs")
    if not df_logs.empty:
        st.dataframe(df_logs.head(100))
    else:
        st.info("No multi-modal logs available.")

# -----------------------------
# Upcoming Reminders Tab
# -----------------------------
with tabs[6]:
    st.subheader("⏰ Upcoming Reminders")
    now = datetime.now()
    upcoming = df_metrics[df_metrics["next_review_time"] > now].sort_values("next_review_time").head(20)
    if not upcoming.empty:
        st.dataframe(upcoming[["concept","next_review_time","memory_score"]])
    else:
        st.info("No upcoming reminders.")
