# dashboard/dashboard_pro.py
import sys
import os
import sqlite3
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Project Root & Modules
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)
from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Load and Clean Data
# -----------------------------
@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)

    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors='coerce')
    df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors='coerce')
    df_sessions["app_name"] = df_sessions["app_name"].fillna("Unknown App")
    df_sessions["audio_label"] = df_sessions["audio_label"].fillna("N/A")
    df_sessions["intent_label"] = df_sessions["intent_label"].fillna("N/A")
    df_sessions["intent_confidence"] = pd.to_numeric(df_sessions["intent_confidence"], errors='coerce').fillna(0)
    df_sessions["duration_min"] = (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60

    df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors='coerce')

    df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
    df_decay["last_seen_ts"] = pd.to_datetime(df_decay["last_seen_ts"], errors='coerce')
    df_decay["updated_at"] = pd.to_datetime(df_decay["updated_at"], errors='coerce')

    df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
    df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors='coerce')

    conn.close()
    return df_sessions, df_logs, df_decay, df_metrics

df_sessions, df_logs, df_decay, df_metrics = load_data()
df_sessions_filtered = df_sessions.dropna(subset=["start_ts", "end_ts"]) if not df_sessions.empty else pd.DataFrame()

# -----------------------------
# Streamlit Page Setup
# -----------------------------
st.set_page_config(page_title="🔮 Forgotten Knowledge Tracker", layout="wide")
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

# Sidebar Tab Navigation
tab_options = ["Overview", "Knowledge Graph", "3D Graph", "Sessions",
               "Memory Decay", "Predicted Forgetting", "Multi-Modal Logs", "Upcoming Reminders"]
selected_tab = st.sidebar.select_slider("Navigate Tabs", options=tab_options)

# -----------------------------
# Part 1: Overview Tab with Modern KPIs
# -----------------------------
if selected_tab == "Overview":
    st.subheader("📊 Dashboard Overview")

    # Metrics
    total_hours = df_sessions_filtered["duration_min"].sum() / 60 if not df_sessions_filtered.empty else 0
    avg_session = df_sessions_filtered["duration_min"].mean() if not df_sessions_filtered.empty else 0
    num_sessions = len(df_sessions_filtered)
    upcoming_reminders = len(df_metrics[df_metrics["next_review_time"] > datetime.now()])

    # Stylish KPI cards
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    kpi_col1.metric(label="Total Hours", value=f"{total_hours:.2f} h")
    kpi_col2.metric(label="Avg Session", value=f"{avg_session:.1f} min")
    kpi_col3.metric(label="Number of Sessions", value=f"{num_sessions}")
    kpi_col4.metric(label="Upcoming Reminders", value=f"{upcoming_reminders}")

    # Daily activity chart
    if not df_sessions_filtered.empty:
        daily_hours = df_sessions_filtered.groupby(df_sessions_filtered["start_ts"].dt.date)["duration_min"].sum() / 60
        fig_daily = px.bar(
            x=daily_hours.index,
            y=daily_hours.values,
            labels={"x":"Date", "y":"Hours"},
            title="Daily Learning Hours",
            color=daily_hours.values,
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_daily, use_container_width=True)
# -----------------------------
# Knowledge Graph Tab (2D)
# -----------------------------
if selected_tab == "Knowledge Graph":
    st.subheader("🕸️ Knowledge Graph (2D)")
    # Sync DB to graph
    sync_db_to_graph()
    G = get_graph()

    if G.nodes:
        # Memory scores for node colors
        memory_scores = [G.nodes[n].get('memory_score', 0.3) for n in G.nodes]
        node_sizes = [node_min_size + (node_max_size - node_min_size) * score for score in memory_scores]
        node_colors = memory_scores  # will use Plotly continuous color scale

        # Prepare Plotly network graph
        pos = nx.spring_layout(G, seed=42, k=0.8)
        edge_x, edge_y = [], []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )

        node_x = [pos[n][0] for n in G.nodes()]
        node_y = [pos[n][1] for n in G.nodes()]
        node_text = [f"{n}<br>Memory Score: {G.nodes[n].get('memory_score',0):.2f}" for n in G.nodes()]

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            textposition="top center",
            text=[n for n in G.nodes()],
            hovertext=node_text,
            marker=dict(
                size=node_sizes,
                color=node_colors,
                colorscale='Viridis',
                colorbar=dict(title="Memory Score"),
                line_width=2
            )
        )

        fig_graph = go.Figure(data=[edge_trace, node_trace],
                              layout=go.Layout(
                                  title='Knowledge Graph',
                                  showlegend=False,
                                  hovermode='closest',
                                  margin=dict(b=20,l=5,r=5,t=40)
                              ))
        st.plotly_chart(fig_graph, use_container_width=True)
    else:
        st.info("Knowledge graph is empty. Start logging sessions to populate it.")

# -----------------------------
# 3D Knowledge Graph Tab
# -----------------------------
if selected_tab == "3D Graph":
    st.subheader("🧩 3D Knowledge Graph (Intent → Keywords)")

    # Fetch intents and keywords from DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT intent_label FROM sessions WHERE intent_label IS NOT NULL")
    intents = [row[0] for row in cursor.fetchall()]

    edges, nodes = [], set()
    for intent in intents:
        cursor.execute("SELECT DISTINCT audio_label || '_' || rowid FROM sessions WHERE intent_label=?", (intent,))
        keywords = [row[0] for row in cursor.fetchall()]
        for kw in keywords:
            edges.append((intent, kw))
            nodes.add(intent)
            nodes.add(kw)
    conn.close()

    if edges:
        G3d = nx.Graph()
        G3d.add_edges_from(edges)
        pos_3d = nx.spring_layout(G3d, dim=3, seed=42)

        # Node positions
        x_nodes = [pos_3d[n][0] for n in G3d.nodes()]
        y_nodes = [pos_3d[n][1] for n in G3d.nodes()]
        z_nodes = [pos_3d[n][2] for n in G3d.nodes()]
        labels = list(G3d.nodes())

        # Edges
        edge_x, edge_y, edge_z = [], [], []
        for edge in G3d.edges():
            x0, y0, z0 = pos_3d[edge[0]]
            x1, y1, z1 = pos_3d[edge[1]]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]
            edge_z += [z0, z1, None]

        fig_3d = go.Figure()

        # Add edges
        fig_3d.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(color='black', width=2),
            hoverinfo='none'
        ))

        # Add nodes
        fig_3d.add_trace(go.Scatter3d(
            x=x_nodes, y=y_nodes, z=z_nodes,
            mode='markers+text',
            marker=dict(size=8, color='orange'),
            text=labels,
            textposition='top center'
        ))

        fig_3d.update_layout(
            scene=dict(
                xaxis_title='X',
                yaxis_title='Y',
                zaxis_title='Z'
            ),
            height=700,
            title="3D Knowledge Graph"
        )
        st.plotly_chart(fig_3d, use_container_width=True)
    else:
        st.info("No intents or keywords found in DB.")

# -----------------------------
# Sessions Tab
# -----------------------------
if selected_tab == "Sessions":
    st.subheader("⏱️ Session Timeline & Heatmap")
    if not df_sessions_filtered.empty:
        df_sess = df_sessions_filtered.copy()
        df_sess["end_ts"] = df_sess["end_ts"].where(df_sess["end_ts"] > df_sess["start_ts"],
                                                    df_sess["start_ts"] + pd.Timedelta(seconds=5))
        df_sess["duration"] = (df_sess["end_ts"] - df_sess["start_ts"]).dt.total_seconds()/60

        # Timeline (Gantt-style)
        fig_tl = px.timeline(df_sess, x_start="start_ts", x_end="end_ts", y="app_name", color="app_name",
                             title="Session Timeline")
        fig_tl.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_tl, use_container_width=True)

        # Heatmap of app usage
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
    else:
        st.info("No session data found.")
# -----------------------------
# Memory Decay Tab
# -----------------------------
if selected_tab == "Memory Decay":
    st.subheader("📉 Memory Decay Curves")

    if not df_decay.empty:
        # Multi-line chart for all concepts
        fig_decay = px.line(
            df_decay,
            x="last_seen_ts",
            y="predicted_recall",
            color="keyword",
            markers=True,
            labels={"last_seen_ts":"Time", "predicted_recall":"Recall Score"},
            title="Memory Decay per Concept"
        )
        fig_decay.update_layout(yaxis=dict(range=[0,1]))
        st.plotly_chart(fig_decay, use_container_width=True)
    else:
        st.info("No memory decay data found.")

# -----------------------------
# Predicted Forgetting Tab
# -----------------------------
if selected_tab == "Predicted Forgetting":
    st.subheader("🔮 Predicted Forgetting Overlay")
    
    if not df_decay.empty:
        concept_list = df_decay["keyword"].unique()
        selected_concept = st.selectbox("Select Concept", concept_list)

        # Exponential decay prediction
        lambda_val = st.slider("Decay Rate (λ)", 0.01, 1.0, 0.1)
        hours = st.slider("Prediction Horizon (hours)", 1, 72, 24)

        df_last = df_decay[df_decay["keyword"] == selected_concept]
        last_score = df_last["predicted_recall"].iloc[-1] if not df_last.empty else 0.5
        times = np.linspace(0, hours, 50)
        predicted_scores = last_score * np.exp(-lambda_val * times)

        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=[datetime.now() + timedelta(hours=t) for t in times],
            y=predicted_scores,
            mode="lines+markers",
            line=dict(color="red"),
            name="Predicted Recall"
        ))
        fig_pred.update_layout(
            yaxis=dict(range=[0,1]),
            xaxis_title="Time",
            yaxis_title="Memory Score",
            title=f"Predicted Forgetting Curve for {selected_concept}"
        )
        st.plotly_chart(fig_pred, use_container_width=True)
    else:
        st.info("No decay data for prediction.")

# -----------------------------
# Multi-Modal Logs Tab
# -----------------------------
if selected_tab == "Multi-Modal Logs":
    st.subheader("🎤 Multi-Modal Logs")

    if not df_logs.empty:
        # Interactive dataframe with filtering
        st.dataframe(df_logs.sort_values("timestamp", ascending=False).head(200))
        # Optional: filter by modality
        modalities = df_logs["modality"].unique() if "modality" in df_logs.columns else []
        if modalities:
            selected_mod = st.multiselect("Filter by modality", modalities)
            if selected_mod:
                st.dataframe(df_logs[df_logs["modality"].isin(selected_mod)].head(200))
    else:
        st.info("No multi-modal logs available.")

# -----------------------------
# Upcoming Reminders Tab
# -----------------------------
if selected_tab == "Upcoming Reminders":
    st.subheader("⏰ Upcoming Reminders")

    now = datetime.now()
    upcoming = df_metrics[df_metrics["next_review_time"] > now].sort_values("next_review_time").head(20)
    
    if not upcoming.empty:
        # Display reminders with memory score color
        def color_row(row):
            if row.memory_score > 0.8:
                return ['background-color: lightgreen']*len(row)
            elif row.memory_score > 0.5:
                return ['background-color: lightyellow']*len(row)
            else:
                return ['background-color: lightcoral']*len(row)

        st.dataframe(upcoming[["concept","next_review_time","memory_score"]].style.apply(color_row, axis=1))
    else:
        st.info("No upcoming reminders.")
