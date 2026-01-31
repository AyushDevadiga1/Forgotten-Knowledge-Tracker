# dashboard/dashboard.py
import sys, os, sqlite3, json, re
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

# -----------------------------
# Project Root
# -----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Streamlit Page Setup & Theme
# -----------------------------
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide")
st.markdown("""
    <style>
    body {background-color: #0b0f14; color: #e6eef3;}
    .stApp {background: linear-gradient(180deg,#071014,#0b0f14);}
    .metric-card {
        background: linear-gradient(160deg, rgba(22,27,34,0.85), rgba(10,12,16,0.6));
        border-radius: 14px; padding: 14px; margin: 6px;
        box-shadow: 0 6px 22px rgba(0,0,0,0.5);
        text-align: center;
    }
    .metric-card h4 {color: #8be9fd; margin:0 0 6px 0;}
    .metric-card p {color: #cdeacb; margin:0; font-size:18px; font-weight:600;}
    .small-muted {color: #8da3b3; font-size:12px;}
    </style>
""", unsafe_allow_html=True)
st.title("🔮 Forgotten Knowledge Tracker — Stylish Dashboard")
st.markdown("Visualize your sessions, memory scores, knowledge graph, reminders, and multi-modal logs interactively.")

# -----------------------------
# Sidebar Controls
# -----------------------------
st.sidebar.title("Tracker Controls")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)

st.sidebar.subheader("Graph Settings")
node_min_size = st.sidebar.slider("Min Node Size", 50, 800, 120)
node_max_size = st.sidebar.slider("Max Node Size", 200, 3000, 700)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.05, 1.0, 0.45)

st.sidebar.subheader("Session Filters")
date_range = st.sidebar.date_input("Filter Sessions by Date Range",
                                   [datetime.now() - timedelta(days=30), datetime.now()])

# -----------------------------
# Utility Functions
# -----------------------------
@st.cache_data(ttl=300)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Sessions
        try:
            df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
            df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors="coerce")
            df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors="coerce")
            df_sessions["app_name"].fillna("Unknown App", inplace=True)
            df_sessions["audio_label"].fillna("N/A", inplace=True)
            df_sessions["intent_label"].fillna("N/A", inplace=True)
            df_sessions["intent_confidence"] = pd.to_numeric(df_sessions.get("intent_confidence",0), errors='coerce').fillna(0)
            df_sessions["duration_min"] = ((df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds()/60).clip(lower=0)
        except Exception:
            df_sessions = pd.DataFrame()

        # Multi-Modal Logs
        try:
            df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
            if "timestamp" in df_logs.columns:
                df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors="coerce")
        except Exception:
            df_logs = pd.DataFrame()

        # Memory Decay
        try:
            df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
            for col in ["last_seen_ts","updated_at"]:
                if col in df_decay.columns:
                    df_decay[col] = pd.to_datetime(df_decay[col], errors="coerce")
        except Exception:
            df_decay = pd.DataFrame()

        # Metrics
        try:
            df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
            if "next_review_time" in df_metrics.columns:
                df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors="coerce")
        except Exception:
            df_metrics = pd.DataFrame()

        return df_sessions, df_logs, df_decay, df_metrics
    finally:
        conn.close()

# -----------------------------
# Load data
# -----------------------------
df_sessions, df_logs, df_decay, df_metrics = load_data()

# Apply date filter
if not df_sessions.empty and "start_ts" in df_sessions.columns:
    start_date, end_date = date_range
    df_sessions = df_sessions[(df_sessions["start_ts"].dt.date >= start_date) &
                              (df_sessions["start_ts"].dt.date <= end_date)]

# -----------------------------
# Load & Sync Knowledge Graph
# -----------------------------
try:
    sync_db_to_graph()
    G = get_graph()
except Exception:
    G = nx.Graph()
concepts = list(G.nodes)

# -----------------------------
# KPI Cards
# -----------------------------
def metric_card(title, value, subtitle=""):
    return f"<div class='metric-card'><h4>{title}</h4><p>{value}</p><div class='small-muted'>{subtitle}</div></div>"

col1, col2, col3, col4 = st.columns(4)
total_hours = (df_sessions["duration_min"].sum()/60) if not df_sessions.empty else 0
avg_session = df_sessions["duration_min"].mean() if not df_sessions.empty else 0
num_sessions = len(df_sessions) if not df_sessions.empty else 0
unique_concepts = len(concepts)

col1.markdown(metric_card("Total Hours", f"{total_hours:.2f} h", "Across filtered sessions"), unsafe_allow_html=True)
col2.markdown(metric_card("Avg Session", f"{avg_session:.1f} min", "Mean session duration"), unsafe_allow_html=True)
col3.markdown(metric_card("Sessions", f"{num_sessions}", "Total sessions loaded"), unsafe_allow_html=True)
col4.markdown(metric_card("Unique Concepts", f"{unique_concepts}", "Nodes in KG"), unsafe_allow_html=True)
st.markdown("---")

# -----------------------------
# Tab Slider Interface
# -----------------------------
tab_names = [
    "Overview", "Knowledge Graph", "3D Graph", "Sessions",
    "Memory Decay", "Predicted Forgetting",
    "Multi-Modal Logs", "Upcoming Reminders"
]
tab_slider = st.slider("Slide to Tab", 0, len(tab_names)-1, 0, format="%d "+tab_names[0])
current_tab = tab_names[tab_slider]

# -----------------------------
# Tab Render Functions
# -----------------------------
def render_overview():
    st.header("📊 Overview")
    if df_sessions.empty:
        st.info("No session data available.")
        return
    recent = df_sessions.sort_values("start_ts").tail(100)
    st.line_chart(recent.set_index("start_ts")["duration_min"].rolling(5).mean())
    mem_list = [{"Concept": n, "Memory Score": G.nodes[n].get("memory_score",0.3)} for n in G.nodes]
    df_mem = pd.DataFrame(mem_list).sort_values("Memory Score", ascending=False)
    st.dataframe(df_mem.head(30))

def render_knowledge_graph():
    st.header("🕸️ Knowledge Graph")
    if len(G.nodes) == 0:
        st.info("Knowledge graph empty. Sync DB to populate nodes.")
        return
    pos2d = nx.spring_layout(G, seed=42, k=0.5)
    mem_scores = [G.nodes[n].get("memory_score",0.3) for n in G.nodes]
    norm = mcolors.Normalize(vmin=0, vmax=1)
    cmap = cm.plasma
    fig, ax = plt.subplots(figsize=(10,8))
    nx.draw_networkx_edges(G, pos2d, alpha=edge_alpha, ax=ax)
    nx.draw_networkx_nodes(G, pos2d, node_size=[node_min_size + (node_max_size-node_min_size)*s for s in mem_scores],
                           node_color=[cmap(norm(s)) for s in mem_scores], ax=ax)
    nx.draw_networkx_labels(G, pos2d, font_size=10, ax=ax)
    st.pyplot(fig)

def render_3d_graph():
    st.header("🧩 3D Knowledge Graph")
    if df_sessions.empty: st.info("No session data"); return
    intents = df_sessions["intent_label"].dropna().unique().tolist()
    edges, nodes = [], set()
    for intent in intents:
        kws = df_sessions[df_sessions["intent_label"]==intent]["audio_label"].dropna().unique()
        for kw in kws: edges.append((intent, kw)); nodes.update([intent,kw])
    if not edges: st.info("No intents or keywords found in DB."); return
    G3d = nx.Graph()
    G3d.add_edges_from(edges)
    pos_3d = nx.spring_layout(G3d, dim=3, seed=42)
    x_nodes = [pos_3d[n][0] for n in G3d.nodes()]; y_nodes = [pos_3d[n][1] for n in G3d.nodes()]; z_nodes = [pos_3d[n][2] for n in G3d.nodes()]
    edge_x, edge_y, edge_z = [], [], []
    for e in G3d.edges(): x0,y0,z0=pos_3d[e[0]]; x1,y1,z1=pos_3d[e[1]]; edge_x+=[x0,x1,None]; edge_y+=[y0,y1,None]; edge_z+=[z0,z1,None]
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(x=edge_x, y=edge_y, z=edge_z, mode='lines', line=dict(color='black', width=2)))
    fig.add_trace(go.Scatter3d(x=x_nodes, y=y_nodes, z=z_nodes, mode='markers+text', text=list(G3d.nodes()),
                               marker=dict(size=6,color='cyan'), textposition='top center'))
    fig.update_layout(scene=dict(xaxis=dict(visible=False),yaxis=dict(visible=False),zaxis=dict(visible=False)), height=700)
    st.plotly_chart(fig, use_container_width=True)

def render_sessions():
    st.header("⏱️ Session Timeline & Heatmap")
    if df_sessions.empty: st.info("No session data."); return
    df_sess = df_sessions.copy()
    df_sess["end_ts"] = df_sess["end_ts"].where(df_sess["end_ts"] > df_sess["start_ts"], df_sess["start_ts"] + pd.Timedelta(seconds=5))
    df_sess["duration"] = (df_sess["end_ts"] - df_sess["start_ts"]).dt.total_seconds()/60
    fig_tl = px.timeline(df_sess, x_start="start_ts", x_end="end_ts", y="app_name", color="app_name")
    fig_tl.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_tl, use_container_width=True)
    heat_df = df_sess.groupby(["app_name", df_sess["start_ts"].dt.date])["duration"].sum().reset_index()
    heat_pivot = heat_df.pivot(index="app_name", columns="start_ts", values="duration").fillna(0)
    fig_hm = go.Figure(data=go.Heatmap(z=heat_pivot.values, x=[str(d) for d in heat_pivot.columns], y=heat_pivot.index, colorscale="Viridis"))
    fig_hm.update_layout(title="App Usage Duration Heatmap")
    st.plotly_chart(fig_hm, use_container_width=True)

def render_memory_decay():
    st.header("📉 Memory Decay Curves")
    if df_decay.empty: st.info("No memory decay data found."); return
    fig_decay = px.line(df_decay, x="last_seen_ts", y="predicted_recall", color="keyword", markers=True,
                        title="Memory Decay Per Concept", labels={"last_seen_ts":"Time","predicted_recall":"Recall"})
    fig_decay.update_layout(yaxis=dict(range=[0,1]))
    st.plotly_chart(fig_decay, use_container_width=True)

def render_predicted_forgetting():
    st.header("📈 Predicted Forgetting")
    if df_decay.empty: st.info("No decay data for prediction."); return
    selected_pred = st.selectbox("Choose concept", df_decay["keyword"].unique())
    lambda_val = 0.1; hours = 24
    df_last = df_decay[df_decay["keyword"]==selected_pred]
    last_score = df_last["predicted_recall"].iloc[-1] if not df_last.empty else 0.5
    times = np.linspace(0,hours,50)
    predicted_scores = last_score*np.exp(-lambda_val*times)
    fig_pred = go.Figure()
    fig_pred.add_trace(go.Scatter(x=[datetime.now()+timedelta(hours=t) for t in times], y=predicted_scores,
                                  mode="lines", name="Predicted Recall"))
    fig_pred.update_layout(yaxis=dict(range=[0,1]), xaxis_title="Time", yaxis_title="Memory Score",
                           title=f"Predicted Forgetting Curve for {selected_pred}")
    st.plotly_chart(fig_pred, use_container_width=True)

def render_multimodal_logs():
    st.header("🎤 Multi-Modal Logs")
    if df_logs.empty: st.info("No multi-modal logs available."); return
    st.dataframe(df_logs.head(100))

def render_upcoming_reminders():
    st.header("⏰ Upcoming Reminders")
    if df_metrics.empty: st.info("No reminders."); return
    now = datetime.now()
    upcoming = df_metrics[df_metrics["next_review_time"] > now].sort_values("next_review_time").head(20)
    if upcoming.empty: st.info("No upcoming reminders."); return
    st.dataframe(upcoming[["concept","next_review_time","memory_score"]])

# -----------------------------
# Tab Dispatcher
# -----------------------------
tab_funcs = {
    "Overview": render_overview,
    "Knowledge Graph": render_knowledge_graph,
    "3D Graph": render_3d_graph,
    "Sessions": render_sessions,
    "Memory Decay": render_memory_decay,
    "Predicted Forgetting": render_predicted_forgetting,
    "Multi-Modal Logs": render_multimodal_logs,
    "Upcoming Reminders": render_upcoming_reminders
}

if current_tab in tab_funcs:
    tab_funcs[current_tab]()
else:
    st.info(f"{current_tab} tab not yet implemented.")
