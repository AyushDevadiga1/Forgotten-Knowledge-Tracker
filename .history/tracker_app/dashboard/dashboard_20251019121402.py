# ==============================================================
# dashboard/dashboard_live_interactive.py — Fully Interactive Live FKT Dashboard
# ==============================================================

import sys, os, sqlite3, time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Load Data
# -----------------------------
@st.cache_data
def load_cleaned_data():
    conn = sqlite3.connect(DB_PATH)
    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors='coerce')
    df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors='coerce')
    df_sessions.fillna({"app_name":"Unknown App","audio_label":"N/A","intent_label":"N/A"}, inplace=True)
    df_sessions["intent_confidence"] = pd.to_numeric(df_sessions["intent_confidence"], errors='coerce').fillna(0)
    df_sessions["duration_min"] = (df_sessions["end_ts"]-df_sessions["start_ts"]).dt.total_seconds()/60

    df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors='coerce')

    df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
    df_decay[["last_seen_ts","updated_at"]] = df_decay[["last_seen_ts","updated_at"]].apply(pd.to_datetime, errors='coerce')

    df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
    df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors='coerce')

    conn.close()
    return df_sessions, df_logs, df_decay, df_metrics

df_sessions, df_logs, df_decay, df_metrics = load_cleaned_data()

# -----------------------------
# Page Setup
# -----------------------------
st.set_page_config(page_title="FKT Dashboard Live Interactive", layout="wide", page_icon="🔮")
st.markdown("<h1 style='text-align:center; color:#4B0082;'>🔮 Forgotten Knowledge Tracker (Live & Interactive)</h1>", unsafe_allow_html=True)
st.markdown("---")

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.header("Settings")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)
st.sidebar.markdown("---")
st.sidebar.header("Graph Visual Settings")
node_min_size = st.sidebar.slider("Min Node Size", 5, 50, 15)
node_max_size = st.sidebar.slider("Max Node Size", 50, 200, 60)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.1, 1.0, 0.5)

# -----------------------------
# Tabs
# -----------------------------
tabs = st.tabs([
    "Overview", "Knowledge Graph", "3D Graph", "Sessions",
    "Memory Decay", "Predicted Forgetting", "Multi-Modal Logs", "Upcoming Reminders"
])

# -----------------------------
# Overview Tab
# -----------------------------
with tabs[0]:
    st.subheader("📊 Overview")
    df_sessions_filtered = df_sessions.dropna(subset=["start_ts","end_ts"])
    total_hours = df_sessions_filtered["duration_min"].sum()/60 if not df_sessions_filtered.empty else 0
    avg_session = df_sessions_filtered["duration_min"].mean() if not df_sessions_filtered.empty else 0
    num_sessions = len(df_sessions_filtered)
    col1, col2, col3 = st.columns(3)
    col1.metric("⏱️ Total Hours", f"{total_hours:.1f} h")
    col2.metric("📝 Avg Session", f"{avg_session:.1f} min")
    col3.metric("📚 Number of Sessions", f"{num_sessions}")

    st.markdown("### Daily Learning Overview")
    if not df_sessions_filtered.empty:
        daily_hours = df_sessions_filtered.groupby(df_sessions_filtered["start_ts"].dt.date)["duration_min"].sum()/60
        fig_daily = px.bar(daily_hours, x=daily_hours.index, y=daily_hours.values,
                           color=daily_hours.values, color_continuous_scale='Viridis',
                           labels={"x":"Date","y":"Hours"})
        st.plotly_chart(fig_daily, use_container_width=True, height=350)
    else:
        st.info("No session data available.")

# -----------------------------
# 3D Knowledge Graph Tab
# -----------------------------
with tabs[2]:
    st.subheader("🧩 3D Knowledge Graph (Live & Interactive)")
    sync_db_to_graph()
    G = get_graph()
    
    if G.nodes:
        pos3d = nx.spring_layout(G, dim=3, seed=42)
        node_labels = list(G.nodes())
        selected_node = st.selectbox("Select Node to Filter", ["All"] + node_labels)

        x_nodes = [pos3d[n][0] for n in G.nodes()]
        y_nodes = [pos3d[n][1] for n in G.nodes()]
        z_nodes = [pos3d[n][2] for n in G.nodes()]
        mem_scores = np.random.rand(len(G.nodes()))
        sizes = [8 + score*12 for score in mem_scores]
        colors = [px.colors.sequential.Viridis[int(score*255)] for score in mem_scores]

        edge_x, edge_y, edge_z = [], [], []
        for e in G.edges():
            x0, y0, z0 = pos3d[e[0]][0], pos3d[e[0]][1], pos3d[e[0]][2]
            x1, y1, z1 = pos3d[e[1]][0], pos3d[e[1]][1], pos3d[e[1]][2]
            edge_x += [x0,x1,None]; edge_y += [y0,y1,None]; edge_z += [z0,z1,None]

        fig3d = go.Figure()
        fig3d.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z, mode='lines', line=dict(color='gray', width=2), hoverinfo='none'))
        fig3d.add_trace(go.Scatter3d(
            x=x_nodes, y=y_nodes, z=z_nodes, mode='markers+text',
            text=node_labels, textposition='top center',
            marker=dict(size=sizes, color=colors, line=dict(width=1, color='black')),
            hovertemplate='<b>%{text}</b><br>Memory Score: %{marker.color:.2f}<extra></extra>'
        ))
        fig3d.update_layout(scene=dict(xaxis_title='X',yaxis_title='Y',zaxis_title='Z'),
                            height=750, title="Animated 3D Knowledge Graph")
        st.plotly_chart(fig3d,use_container_width=True)
    else:
        st.info("Knowledge graph empty.")

# -----------------------------
# Filtered Sessions Tab
# -----------------------------
with tabs[3]:
    st.subheader("⏱️ Sessions (Filtered)")
    if selected_node != "All":
        df_sessions_filtered = df_sessions[(df_sessions["intent_label"]==selected_node) | 
                                          (df_sessions["audio_label"]==selected_node)]
    else:
        df_sessions_filtered = df_sessions
    if not df_sessions_filtered.empty:
        df_sess = df_sessions_filtered.copy()
        df_sess["end_ts"] = df_sess["end_ts"].where(df_sess["end_ts"]>df_sess["start_ts"], df_sess["start_ts"]+pd.Timedelta(seconds=5))
        df_sess["duration"] = (df_sess["end_ts"]-df_sess["start_ts"]).dt.total_seconds()/60

        fig_tl = px.timeline(df_sess, x_start="start_ts", x_end="end_ts", y="app_name", color="app_name",
                             hover_data=["audio_label","intent_label"])
        fig_tl.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_tl, use_container_width=True, height=500)

        heat_df = df_sess.groupby(["app_name", df_sess["start_ts"].dt.date])["duration"].sum().reset_index()
        heat_pivot = heat_df.pivot(index="app_name", columns="start_ts", values="duration").fillna(0)
        fig_hm = go.Figure(data=go.Heatmap(
            z=heat_pivot.values,
            x=[str(d) for d in heat_pivot.columns],
            y=heat_pivot.index,
            colorscale="Viridis",
            hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} min<extra></extra>"
        ))
        fig_hm.update_layout(title="App Usage Heatmap", height=400)
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.info("No session data for this node.")

# -----------------------------
# Filtered Memory Decay Tab
# -----------------------------
with tabs[4]:
    st.subheader("📉 Memory Decay (Filtered)")
    radar_placeholder = st.empty()
    df_decay_filtered = df_decay if selected_node=="All" else df_decay[df_decay["keyword"]==selected_node]
    if not df_decay_filtered.empty:
        latest_decay = df_decay_filtered.groupby("keyword")["predicted_recall"].last()
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=latest_decay.values,
            theta=latest_decay.index,
            fill='toself',
            line=dict(color='orange')
        ))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,1])),
                                title="Memory Recall Radar",height=500)
        radar_placeholder.plotly_chart(fig_radar,use_container_width=True)
    else:
        st.info("No decay data for this node.")

# -----------------------------
# Filtered Predicted Forgetting Tab
# -----------------------------
with tabs[5]:
    st.subheader("📈 Predicted Forgetting (Filtered)")
    pred_placeholder = st.empty()
    df_decay_filtered = df_decay if selected_node=="All" else df_decay[df_decay["keyword"]==selected_node]
    if not df_decay_filtered.empty:
        selected_pred = df_decay_filtered["keyword"].unique()[0] if selected_node!="All" else df_decay_filtered["keyword"].unique()[0]
        last_score = df_decay_filtered[df_decay_filtered["keyword"]==selected_pred]["predicted_recall"].iloc[-1]
        times = np.linspace(0,24,50)
        decay_factor = np.exp(-0.1*times)
        predicted_scores = last_score*decay_factor
        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=[datetime.now()+timedelta(hours=t) for t in times],
            y=predicted_scores,
            mode='lines+markers',
            line=dict(color='orange',width=3),
            marker=dict(size=6)
        ))
        fig_pred.update_layout(yaxis=dict(range=[0,1]), xaxis_title="Time", yaxis_title="Memory Score",
                                title=f"Predicted Forgetting Curve for {selected_pred}",height=500)
        pred_placeholder.plotly_chart(fig_pred,use_container_width=True)
    else:
        st.info("No decay data for this node.")

# -----------------------------
# Upcoming Reminders Tab
# -----------------------------
with tabs[7]:
    st.subheader("⏰ Upcoming Reminders (Filtered)")
    df_metrics_filtered = df_metrics if selected_node=="All" else df_metrics[df_metrics["concept"]==selected_node]
    now = datetime.now()
    upcoming = df_metrics_filtered[df_metrics_filtered["next_review_time"]>now].sort_values("next_review_time").head(20)
    if not upcoming.empty:
        st.dataframe(upcoming[["concept","next_review_time","memory_score"]])
    else:
        st.info("No upcoming reminders for this node.")
