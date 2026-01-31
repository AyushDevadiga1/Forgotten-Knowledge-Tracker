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

def parse_ocr_keywords(val):
    if val is None or pd.isna(val):
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        val = val.strip()
        if val.startswith("{") or val.startswith("["):
            try: return json.loads(val)
            except: pass
        # fallback comma-separated
        return {k.strip(): {"score":0.5} for k in re.split(r"[,\n;]+", val) if k.strip()}
    return {}

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
    "Multi-Modal Logs", "Upcoming Reminders",
    "OCR Insights", "Audio / Intent Analysis",
    "Performance Insights", "System Health"
]
tab_slider = st.slider("Slide to Tab", 0, len(tab_names)-1, 0, format="%d "+tab_names[0])
current_tab = tab_names[tab_slider]

# -----------------------------
# Render Tabs
# -----------------------------
def render_overview():
    st.header("Overview")
    if df_sessions.empty:
        st.info("No session data available.")
        return
    recent = df_sessions.sort_values("start_ts").tail(100)
    st.line_chart(recent.set_index("start_ts")["duration_min"].rolling(5).mean())
    mem_list = [{"Concept": n, "Memory Score": G.nodes[n].get("memory_score",0.3)} for n in G.nodes]
    df_mem = pd.DataFrame(mem_list).sort_values("Memory Score")
    st.dataframe(df_mem.head(30))

def render_knowledge_graph():
    st.header("Knowledge Graph")
    if len(G.nodes) == 0:
        st.info("Knowledge graph empty. Sync DB to populate nodes.")
        return
    pos2d = nx.spring_layout(G, seed=42, k=0.5)
    centrality = nx.degree_centrality(G)
    x, y, text, size, color = [], [], [], [], []
    mem_scores = [G.nodes[n].get("memory_score",0.3) for n in G.nodes]
    norm = mcolors.Normalize(vmin=0, vmax=1)
    cmap = cm.plasma
    for i,n in enumerate(G.nodes):
        px, py = pos2d[n]
        x.append(px); y.append(py)
        text.append(f"{n}<br>Memory: {mem_scores[i]:.2f}")
        size.append(node_min_size + (node_max_size-node_min_size)*mem_scores[i])
        color.append(cmap(norm(mem_scores[i])))
    fig, ax = plt.subplots(figsize=(10,8))
    nx.draw_networkx_edges(G, pos2d, alpha=edge_alpha, ax=ax)
    nx.draw_networkx_nodes(G, pos2d, node_size=size, node_color=color, ax=ax)
    nx.draw_networkx_labels(G, pos2d, font_size=10, ax=ax)
    st.pyplot(fig)

def render_3d_graph():
    st.header("3D Knowledge Graph")
    intents = df_sessions["intent_label"].dropna().unique().tolist() if not df_sessions.empty else []
    edges, nodes, labels = [], set(), []
    # Build edges: Intent → Audio
    for intent in intents:
        kws = df_sessions[df_sessions["intent_label"]==intent]["audio_label"].dropna().unique()
        for kw in kws:
            edges.append((intent, kw))
            nodes.add(intent)
            nodes.add(kw)
    if not edges:
        st.info("No intents or keywords found in DB.")
        return
    G3d = nx.Graph()
    G3d.add_edges_from(edges)
    pos_3d = nx.spring_layout(G3d, dim=3, seed=42)
    x_nodes = [pos_3d[n][0] for n in G3d.nodes()]
    y_nodes = [pos_3d[n][1] for n in G3d.nodes()]
    z_nodes = [pos_3d[n][2] for n in G3d.nodes()]
    edge_x, edge_y, edge_z = [], [], []
    for e in G3d.edges():
        x0,y0,z0 = pos_3d[e[0]]
        x1,y1,z1 = pos_3d[e[1]]
        edge_x += [x0,x1,None]; edge_y += [y0,y1,None]; edge_z += [z0,z1,None]
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(x=edge_x, y=edge_y, z=edge_z, mode='lines', line=dict(color='black', width=2)))
    fig.add_trace(go.Scatter3d(x=x_nodes, y=y_nodes, z=z_nodes, mode='markers+text', text=list(G3d.nodes()),
                               marker=dict(size=6,color='cyan'), textposition='top center'))
    fig.update_layout(scene=dict(xaxis=dict(visible=False),yaxis=dict(visible=False),zaxis=dict(visible=False)),
                      height=700)
    st.plotly_chart(fig, use_container_width=True)

# Tab Dispatcher
tab_funcs = {
    "Overview": render_overview,
    "Knowledge Graph": render_knowledge_graph,
    "3D Graph": render_3d_graph,
    # You can implement remaining tabs similarly
}

if current_tab in tab_funcs:
    tab_funcs[current_tab]()
else:
    st.info(f"{current_tab} tab not yet implemented. Placeholder.")

