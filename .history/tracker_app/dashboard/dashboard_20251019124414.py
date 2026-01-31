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
from wordcloud import WordCloud

# Fix font warnings in matplotlib
plt.rcParams['font.sans-serif'] = ['Arial']

# Project Root
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Load & Clean Data
# -----------------------------
@st.cache_data
def load_cleaned_data():
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

df_sessions, df_logs, df_decay, df_metrics = load_cleaned_data()

# -----------------------------
# Streamlit Page Setup
# -----------------------------
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide")
st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Visualize learning sessions, memory scores, knowledge graph, upcoming reminders, and more.")

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
    "Overview", "Knowledge Graph", "3D Graph", "Sessions",
    "Memory Decay", "Predicted Forgetting",
    "Multi-Modal Logs", "Upcoming Reminders"
])

# -----------------------------
# Overview Tab (Enhanced & Lightweight)
# -----------------------------
with tabs[0]:
    st.subheader("📊 Study Analytics Dashboard")
    df_s = df_sessions.dropna(subset=["start_ts","end_ts"])
    if df_s.empty:
        st.info("No session data found.")
    else:
        total_hours = df_s["duration_min"].sum() / 60
        avg_session = df_s["duration_min"].mean()
        num_sessions = len(df_s)
        total_idle = df_s[df_s['interaction_count'] == 0]["duration_min"].sum()
        active_time = total_hours*60 - total_idle
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Hours Studied", f"{total_hours:.2f} h")
        col2.metric("Average Session", f"{avg_session:.1f} min")
        col3.metric("Number of Sessions", f"{num_sessions}")
        col4.metric("Idle Time", f"{total_idle:.1f} min")
        
        # Daily Study Trend
        daily_hours = df_s.groupby(df_s["start_ts"].dt.date)["duration_min"].sum() / 60
        st.markdown("### Daily Study Hours")
        st.line_chart(daily_hours, height=200)
        
        # Top 10 Apps (bar chart)
        top_apps = df_s.groupby("app_name")["duration_min"].sum().nlargest(10)
        st.markdown("### Top 10 Apps Used")
        st.bar_chart(top_apps)
        
        # Keyword Cloud (top 50)
        st.markdown("### Keyword Cloud / Frequency")
        top_keywords = df_s['audio_label'].value_counts().nlargest(50)
        wordcloud = WordCloud(width=800, height=300, background_color="white").generate_from_frequencies(top_keywords)
        fig_wc, ax_wc = plt.subplots(figsize=(12,4))
        ax_wc.imshow(wordcloud, interpolation='bilinear')
        ax_wc.axis("off")
        st.pyplot(fig_wc)

        # Idle vs Active (bar chart)
        st.markdown("### Active vs Idle Time (min)")
        st.bar_chart(pd.Series([active_time, total_idle], index=["Active", "Idle"]))
        
        # Session Duration Distribution (histogram)
        st.markdown("### Session Duration Distribution (min)")
        fig_hist = px.histogram(df_s, x="duration_min", nbins=20, title="Session Durations", labels={"duration_min":"Minutes"})
        st.plotly_chart(fig_hist, use_container_width=True)

        # Top Keywords Table
        st.markdown("### Most Repeated Keywords / Occurrences")
        keyword_table = df_s.groupby('audio_label').agg(
            Occurrences=('audio_label','count'),
            Avg_Confidence=('intent_confidence','mean')
        ).sort_values('Occurrences', ascending=False).head(10)
        st.dataframe(keyword_table)
        
        # Heatmap: App Usage by Day (lightweight)
        st.markdown("### App Usage Heatmap")
        heat_df = df_s.groupby(["app_name", df_s["start_ts"].dt.date])["duration_min"].sum().reset_index()
        heat_pivot = heat_df.pivot(index="app_name", columns="start_ts", values="duration_min").fillna(0)
        fig_hm = go.Figure(data=go.Heatmap(
            z=heat_pivot.values,
            x=[str(d) for d in heat_pivot.columns],
            y=heat_pivot.index,
            colorscale="Viridis",
            hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} min<extra></extra>"
        ))
        fig_hm.update_layout(height=400, title="Daily App Usage")
        st.plotly_chart(fig_hm, use_container_width=True)

# -----------------------------
# Knowledge Graph Tab (2D optimized)
# -----------------------------
with tabs[1]:
    st.subheader("🕸️ Knowledge Graph")
    sync_db_to_graph()
    G = get_graph()
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
# 3D Knowledge Graph Tab (optimized)
# -----------------------------
with tabs[2]:
    st.subheader("🧩 3D Knowledge Graph (Intent → Keywords)")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT intent_label FROM sessions WHERE intent_label IS NOT NULL")
    intents = [row[0] for row in cursor.fetchall()]
    edges = []
    for intent in intents:
        cursor.execute("SELECT DISTINCT audio_label || '_' || rowid FROM sessions WHERE intent_label=?", (intent,))
        keywords = [row[0] for row in cursor.fetchall()]
        for kw in keywords:
            edges.append((intent, kw))
    conn.close()
    
    if edges:
        G3d = nx.Graph()
        G3d.add_edges_from(edges)
        pos_3d = nx.spring_layout(G3d, dim=3, seed=42)
        x_nodes, y_nodes, z_nodes, labels = [], [], [], []
        for n in G3d.nodes():
            x_nodes.append(pos_3d[n][0])
            y_nodes.append(pos_3d[n][1])
            z_nodes.append(pos_3d[n][2])
            labels.append(n)
        edge_x, edge_y, edge_z = [], [], []
        for e in G3d.edges():
            x0, y0, z0 = pos_3d[e[0]]
            x1, y1, z1 = pos_3d[e[1]]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]
            edge_z += [z0, z1, None]
        fig_3d = go.Figure()
        fig_3d.add_trace(go.Scatter3d(x=edge_x, y=edge_y, z=edge_z, mode='lines', line=dict(color='black', width=2), hoverinfo='none'))
        fig_3d.add_trace(go.Scatter3d(x=x_nodes, y=y_nodes, z=z_nodes, mode='markers+text', marker=dict(size=6, color='orange'),
                                      text=labels, textposition='top center'))
        fig_3d.update_layout(scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z'), height=700,
                             title="3D Knowledge Graph")
        st.plotly_chart(fig_3d, use_container_width=True)
    else:
        st.info("No intents or keywords found in DB.")

# -----------------------------
# Sessions Tab
# -----------------------------
with tabs[3]:
    st.subheader("⏱️ Session Timeline & Heatmap")
    if not df_s.empty:
        df_sess = df_s.copy()
        df_sess["end_ts"] = df_sess["end_ts"].where(df_sess["end_ts"] > df_sess["start_ts"], df_sess["start_ts"] + pd.Timedelta(seconds=5))
        df_sess["duration"] = (df_sess["end_ts"] - df_sess["start_ts"]).dt.total_seconds()/60
        fig_tl = px.timeline(df_sess, x_start="start_ts", x_end="end_ts", y="app_name", color="app_name")
        fig_tl.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_tl, use_container_width=True)

        heat_df = df_sess.groupby(["app_name", df_sess["start_ts"].dt.date])["duration"].sum().reset_index()
        heat_pivot = heat_df.pivot(index="app_name", columns="start_ts", values="duration").fillna(0)
        fig_hm = go.Figure(data=go.Heatmap(z=heat_pivot.values, x=[str(d) for d in heat_pivot.columns],
                                           y=heat_pivot.index, colorscale="Viridis"))
        fig_hm.update_layout(title="App Usage Duration Heatmap", height=400)
        st.plotly_chart(fig_hm, use_container_width=True)

# -----------------------------
# Memory Decay Tab
# -----------------------------
with tabs[4]:
    st.subheader("📉 Memory Decay Curves")
    if not df_decay.empty:
        fig_decay = px.line(df_decay, x="last_seen_ts", y="predicted_recall", color="keyword", markers=True,
                            labels={"last_seen_ts":"Time","predicted_recall":"Recall"})
        fig_decay.update_layout(yaxis=dict(range=[0,1]), height=400)
        st.plotly_chart(fig_decay, use_container_width=True)
    else:
        st.info("No memory decay data found.")

# -----------------------------
# Predicted Forgetting Tab
# -----------------------------
with tabs[5]:
    st.subheader("📈 Predicted Forgetting Overlay")
    if not df_decay.empty:
        selected_pred = st.selectbox("Choose concept", df_decay["keyword"].unique())
        lambda_val = 0.1
        hours = 24
        df_last = df_decay[df_decay["keyword"]==selected_pred]
        last_score = df_last["predicted_recall"].iloc[-1] if not df_last.empty else 0.5
        times = np.linspace(0, hours, 50)
        predicted_scores = last_score * np.exp(-lambda_val * times)
        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(x=[datetime.now() + timedelta(hours=t) for t in times], y=predicted_scores,
                                      mode="lines", name="Predicted Recall"))
        fig_pred.update_layout(yaxis=dict(range=[0,1]), xaxis_title="Time", yaxis_title="Memory Score", height=400)
        st.plotly_chart(fig_pred, use_container_width=True)
    else:
        st.info("No decay data for prediction.")

# -----------------------------
# Multi-Modal Logs Tab
# -----------------------------
with tabs[6]:
    st.subheader("🎤 Multi-Modal Logs")
    if not df_logs.empty:
        st.dataframe(df_logs.head(100))
    else:
        st.info("No multi-modal logs available.")

# -----------------------------
# Upcoming Reminders Tab
# -----------------------------
with tabs[7]:
    st.subheader("⏰ Upcoming Reminders")
    now = datetime.now()
    upcoming = df_metrics[df_metrics["next_review_time"] > now].sort_values("next_review_time").head(20)
    if not upcoming.empty:
        st.dataframe(upcoming[["concept","next_review_time","memory_score"]])
    else:
        st.info("No upcoming reminders.")
