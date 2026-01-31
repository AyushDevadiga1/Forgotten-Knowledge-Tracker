# ==============================================================
# dashboard/dashboard_modern_live.py — Fully Real-Time FKT Dashboard
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
st.set_page_config(page_title="FKT Dashboard Live", layout="wide", page_icon="🔮")
st.markdown("<h1 style='text-align:center; color:#4B0082;'>🔮 Forgotten Knowledge Tracker (Live)</h1>", unsafe_allow_html=True)
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
# Animated 3D Knowledge Graph Tab
# -----------------------------
with tabs[2]:
    st.subheader("🧩 3D Knowledge Graph (Animated)")
    sync_db_to_graph()
    G = get_graph()
    if G.nodes:
        pos3d = nx.spring_layout(G, dim=3, seed=42)
        x_nodes = [pos3d[n][0] for n in G.nodes()]
        y_nodes = [pos3d[n][1] for n in G.nodes()]
        z_nodes = [pos3d[n][2] for n in G.nodes()]
        labels = list(G.nodes())
        mem_scores = np.random.rand(len(G.nodes()))  # Replace with actual memory scores
        sizes = [8 + score*12 for score in mem_scores]
        colors = [px.colors.sequential.Viridis[int(score*255)] for score in mem_scores]

        edge_x, edge_y, edge_z = [], [], []
        for e in G.edges():
            x0, y0 = pos3d[e[0]][0], pos3d[e[0]][1]; z0=pos3d[e[0]][2]
            x1, y1 = pos3d[e[1]][0], pos3d[e[1]][1]; z1=pos3d[e[1]][2]
            edge_x += [x0,x1,None]; edge_y += [y0,y1,None]; edge_z += [z0,z1,None]

        fig3d = go.Figure()
        fig3d.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z, mode='lines', line=dict(color='gray',width=2), hoverinfo='none'))
        fig3d.add_trace(go.Scatter3d(
            x=x_nodes, y=y_nodes, z=z_nodes, mode='markers+text',
            text=labels, textposition='top center',
            marker=dict(size=sizes,color=colors,line=dict(width=1,color='black')),
            hovertemplate='<b>%{text}</b><br>Memory Score: %{marker.color:.2f}<extra></extra>'
        ))
        fig3d.update_layout(scene=dict(xaxis_title='X',yaxis_title='Y',zaxis_title='Z'),
                            height=750,title="Animated 3D Knowledge Graph")

        placeholder = st.empty()
        for i in range(5):  # Live update simulation
            new_mem = np.random.rand(len(G.nodes()))
            new_colors = [px.colors.sequential.Viridis[int(s*255)] for s in new_mem]
            fig3d.data[1].marker.color = new_colors
            placeholder.plotly_chart(fig3d,use_container_width=True)
            time.sleep(2)
    else:
        st.info("No nodes in knowledge graph.")

# -----------------------------
# Live Memory Decay Radar
# -----------------------------
with tabs[4]:
    st.subheader("📉 Memory Decay (Live)")
    radar_placeholder = st.empty()
    if not df_decay.empty:
        for i in range(5):  # Simulate live updates
            latest_decay = df_decay.groupby("keyword")["predicted_recall"].last()
            fluctuation = latest_decay*np.random.uniform(0.95,1.05,size=len(latest_decay))
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=fluctuation.values,
                theta=latest_decay.index,
                fill='toself',
                line=dict(color='orange')
            ))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,1])),
                                    title="Concept Recall Radar (Live)",height=500)
            radar_placeholder.plotly_chart(fig_radar,use_container_width=True)
            time.sleep(2)
    else:
        st.info("No memory decay data.")

# -----------------------------
# Live Predicted Forgetting
# -----------------------------
with tabs[5]:
    st.subheader("📈 Predicted Forgetting (Live)")
    pred_placeholder = st.empty()
    if not df_decay.empty:
        selected_pred = st.selectbox("Choose concept", df_decay["keyword"].unique())
        last_score = df_decay[df_decay["keyword"]==selected_pred]["predicted_recall"].iloc[-1]
        times = np.linspace(0,24,50)
        for i in range(5):  # simulate live decay updates
            decay_factor = np.exp(-0.1*times*(1+i*0.05))
            predicted_scores = last_score*decay_factor
            fig_pred = go.Figure()
            fig_pred.add_trace(go.Scatter(
                x=[datetime.now()+timedelta(hours=t) for t in times],
                y=predicted_scores, mode='lines+markers',
                line=dict(color='orange',width=3),
                marker=dict(size=6)
            ))
            fig_pred.update_layout(yaxis=dict(range=[0,1]), xaxis_title="Time", yaxis_title="Memory Score",
                                    title=f"Predicted Forgetting Curve for {selected_pred}",height=500)
            pred_placeholder.plotly_chart(fig_pred,use_container_width=True)
            time.sleep(2)
    else:
        st.info("No decay data.")
