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

plt.rcParams['font.sans-serif'] = ['Arial']

# Project Root
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Load Data
# -----------------------------
def load_cleaned_data():
    conn = sqlite3.connect(DB_PATH)
    # Sessions
    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors='coerce')
    df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors='coerce')
    df_sessions["duration_min"] = ((df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60).fillna(0)
    df_sessions["app_name"] = df_sessions["app_name"].fillna("Unknown App")
    df_sessions["intent_label"] = df_sessions["intent_label"].fillna("N/A")
    df_sessions["intent_confidence"] = pd.to_numeric(df_sessions["intent_confidence"], errors='coerce').fillna(0)

    # Multi-modal logs
    df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors='coerce')

    # Memory decay
    df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
    df_decay["last_seen_ts"] = pd.to_datetime(df_decay["last_seen_ts"], errors='coerce')
    df_decay["updated_at"] = pd.to_datetime(df_decay["updated_at"], errors='coerce')

    # Metrics / reminders
    df_metrics = pd.read_sql("SELECT concept, next_review_time, memory_score FROM metrics", conn)
    df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors='coerce')

    # Keywords
    try:
        df_keywords = pd.read_sql("SELECT intent_label, keyword FROM multi_modal_keywords", conn)
    except:
        df_keywords = pd.DataFrame(columns=["intent_label", "keyword"])

    conn.close()
    return df_sessions, df_logs, df_decay, df_metrics, df_keywords

df_sessions, df_logs, df_decay, df_metrics, df_keywords = load_cleaned_data()

# -----------------------------
# Streamlit Setup
# -----------------------------
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide")
st.title("🔮 Forgotten Knowledge Tracker Dashboard")

# Sidebar
st.sidebar.title("Settings")
camera_on = st.sidebar.checkbox("Enable Webcam")
audio_on = st.sidebar.checkbox("Enable Audio", True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", True)
st.sidebar.markdown("---")
st.sidebar.subheader("Graph Settings")
node_min_size = st.sidebar.slider("Min Node Size", 50, 500, 150)
node_max_size = st.sidebar.slider("Max Node Size", 100, 2000, 800)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.1, 1.0, 0.5)

# -----------------------------
# Tabs
# -----------------------------
tabs = st.tabs([
    "Overview", "Knowledge Graph", "3D Intent-Keyword Map",
    "Sessions", "Memory Decay", "Predicted Forgetting",
    "Multi-Modal Logs", "Upcoming Reminders"
])

# -----------------------------
# Overview Tab
# -----------------------------
with tabs[0]:
    st.subheader("📊 Dashboard Overview")
    df_sess_filt = df_sessions.dropna(subset=["start_ts","end_ts"])
    total_hours = df_sess_filt["duration_min"].sum() / 60
    avg_session = df_sess_filt["duration_min"].mean()
    num_sessions = len(df_sess_filt)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Hours", f"{total_hours:.2f} h")
    c2.metric("Avg Session", f"{avg_session:.1f} min")
    c3.metric("Number of Sessions", num_sessions)
    if not df_sess_filt.empty:
        daily_hours = df_sess_filt.groupby(df_sess_filt["start_ts"].dt.date)["duration_min"].sum()/60
        c4.line_chart(daily_hours)

# -----------------------------
# Knowledge Graph Tab
# -----------------------------
with tabs[1]:
    st.subheader("🕸️ Knowledge Graph")
    sync_db_to_graph()
    G = get_graph()
    if G.nodes:
        scores = [G.nodes[n].get("memory_score",0.3) for n in G.nodes]
        sizes = [node_min_size + s*(node_max_size-node_min_size) for s in scores]
        colors = [cm.viridis(s) for s in scores]
        pos = nx.spring_layout(G, seed=42)
        fig, ax = plt.subplots(figsize=(12,10))
        nx.draw(G, pos, with_labels=True, node_size=sizes, node_color=colors, alpha=edge_alpha, ax=ax)
        st.pyplot(fig)
    else:
        st.info("Knowledge graph empty")

# -----------------------------
# 3D Intent-Keyword Map
# -----------------------------
with tabs[2]:
    st.subheader("🧩 3D Intent-Keyword Map")
    if not df_keywords.empty:
        G3 = nx.Graph()
        for _, row in df_keywords.iterrows():
            intent = row["intent_label"]
            kw = row["keyword"]
            G3.add_node(intent, group="intent")
            G3.add_node(kw, group="keyword")
            G3.add_edge(intent, kw)
        pos3 = nx.spring_layout(G3, dim=3, seed=42)
        x,y,z = [],[],[]
        for n in G3.nodes:
            x.append(pos3[n][0]*10)
            y.append(pos3[n][1]*10)
            z.append(pos3[n][2]*10)
        edge_x,edge_y,edge_z=[],[],[]
        for e in G3.edges:
            edge_x += [pos3[e[0]][0]*10,pos3[e[1]][0]*10,None]
            edge_y += [pos3[e[0]][1]*10,pos3[e[1]][1]*10,None]
            edge_z += [pos3[e[0]][2]*10,pos3[e[1]][2]*10,None]
        edge_trace = go.Scatter3d(x=edge_x, y=edge_y, z=edge_z, mode='lines', line=dict(color='gray', width=2))
        node_trace = go.Scatter3d(
            x=x, y=y, z=z, mode='markers+text',
            marker=dict(size=8, color=['red' if G3.nodes[n]['group']=='intent' else 'blue' for n in G3.nodes]),
            text=list(G3.nodes), textposition='top center'
        )
        fig3d = go.Figure(data=[edge_trace,node_trace])
        fig3d.update_layout(scene=dict(xaxis=dict(title='X'), yaxis=dict(title='Y'), zaxis=dict(title='Z')))
        st.plotly_chart(fig3d, use_container_width=True)
    else:
        st.info("No keywords available")

# -----------------------------
# Sessions Tab
# -----------------------------
with tabs[3]:
    st.subheader("⏱️ Sessions")
    if not df_sess_filt.empty:
        df_sess_filt["duration"] = df_sess_filt["duration_min"]
        fig_tl = px.timeline(df_sess_filt, x_start="start_ts", x_end="end_ts", y="app_name", color="app_name")
        fig_tl.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_tl)
        # Heatmap
        heat = df_sess_filt.groupby(["app_name", df_sess_filt["start_ts"].dt.date])["duration"].sum().reset_index()
        pivot = heat.pivot(index="app_name", columns="start_ts", values="duration").fillna(0)
        fig_h = go.Figure(data=go.Heatmap(
            z=pivot.values, x=[str(d) for d in pivot.columns], y=pivot.index, colorscale="Viridis"
        ))
        st.plotly_chart(fig_h)
    else:
        st.info("No sessions found")

# -----------------------------
# Memory Decay Tab
# -----------------------------
with tabs[4]:
    st.subheader("📉 Memory Decay")
    if G.nodes:
        fig_decay = go.Figure()
        for n in G.nodes:
            scores = [G.nodes[n].get("memory_score",0.3)]
            times = [datetime.now()]
            fig_decay.add_trace(go.Scatter(x=times, y=scores, mode='lines+markers', name=n))
        fig_decay.update_layout(yaxis=dict(range=[0,1]))
        st.plotly_chart(fig_decay)
    else:
        st.info("No memory decay data")

# -----------------------------
# Predicted Forgetting
# -----------------------------
with tabs[5]:
    st.subheader("📈 Predicted Forgetting")
    if G.nodes:
        concept = st.selectbox("Choose concept", list(G.nodes))
        if concept:
            last_score = G.nodes[concept].get("memory_score",0.3)
            t = np.linspace(0,24,50)
            pred = last_score*np.exp(-0.1*t)
            fig_pred = go.Figure()
            fig_pred.add_trace(go.Scatter(x=[datetime.now()+timedelta(hours=i) for i in t], y=pred, mode='lines'))
            fig_pred.update_layout(yaxis=dict(range=[0,1]))
            st.plotly_chart(fig_pred)
    else:
        st.info("No concepts found")

# -----------------------------
# Multi-Modal Logs
# -----------------------------
with tabs[6]:
    st.subheader("🎤 Multi-Modal Logs")
    if not df_logs.empty:
        st.dataframe(df_logs.head(100))
    else:
        st.info("No logs found")

# -----------------------------
# Upcoming Reminders
# -----------------------------
with tabs[7]:
    st.subheader("⏰ Upcoming Reminders")
    now = datetime.now()
    upcoming = df_metrics[df_metrics["next_review_time"] > now].sort_values("next_review_time")
    if not upcoming.empty:
        st.dataframe(upcoming.head(20))
    else:
        st.info("No upcoming reminders")
