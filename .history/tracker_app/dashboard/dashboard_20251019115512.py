# dashboard/offline_tracker_dashboard.py
"""
Offline Tracker Dashboard — Dark theme + stats-rich + 2D graph
"""

import sys, os, sqlite3, json, re
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------
# Paths
# ----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# ----------------------------
# Page config + offline-friendly theme
# ----------------------------
st.set_page_config(page_title="FKT Tracker — Offline Stats Dashboard", layout="wide")
st.markdown("""
<style>
:root{
    --bg:#1a1a2e;
    --panel:#162447;
    --card:#1f4068;
    --primary:#e43f5a;
    --accent:#00b7c2;
    --muted:#b0b0b0;
}
body, .stApp, .main { background-color: var(--bg); color: #fff; font-family: monospace; }
.neon-card {
    background: var(--card); border-radius:12px; padding:10px; margin-bottom:10px;
}
.kpi { background: var(--card); padding:8px; border-radius:10px; text-align:center; }
.kpi h3 { margin:2px; color: var(--primary); }
.kpi small { color: var(--muted); }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='color:#00b7c2;'>⚡ FKT Tracker — Offline Dashboard</h1>", unsafe_allow_html=True)

# ----------------------------
# Utility functions
# ----------------------------
def table_exists(conn, table_name):
    try:
        return conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'").fetchone() is not None
    except:
        return False

@st.cache_data(ttl=300)
def load_tables():
    """Load DB tables safely"""
    conn = sqlite3.connect(DB_PATH)
    try:
        df_sessions = pd.read_sql("SELECT * FROM sessions", conn) if table_exists(conn, "sessions") else pd.DataFrame()
        df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn) if table_exists(conn, "multi_modal_logs") else pd.DataFrame()
        df_decay = pd.read_sql("SELECT * FROM memory_decay", conn) if table_exists(conn, "memory_decay") else pd.DataFrame()
        df_metrics = pd.read_sql("SELECT * FROM metrics", conn) if table_exists(conn, "metrics") else pd.DataFrame()
    except Exception as e:
        df_sessions, df_logs, df_decay, df_metrics = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        print("DB read error:", e)
    finally:
        conn.close()
    # Convert timestamps
    for df, cols in [(df_sessions, ["start_ts","end_ts"]),
                     (df_logs, ["timestamp"]),
                     (df_decay, ["last_seen_ts","updated_at"]),
                     (df_metrics, ["next_review_time","last_updated"])]:
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors='coerce')
    return df_sessions, df_logs, df_decay, df_metrics

def parse_ocr_keywords(val):
    if pd.isna(val):
        return []
    if isinstance(val, str):
        try: return list(json.loads(val).keys())
        except: return re.split(r"[,\n;]+", val)
    if isinstance(val, dict):
        return list(val.keys())
    return []

@st.cache_data(ttl=300)
def graph_layout(nodes, edges):
    """2D spring layout"""
    G = nx.Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    pos = nx.spring_layout(G, seed=42)
    return {n: (float(p[0]), float(p[1])) for n, p in pos.items()}

# ----------------------------
# Load data
# ----------------------------
df_sessions, df_logs, df_decay, df_metrics = load_tables()

# ----------------------------
# Sidebar filters
# ----------------------------
st.sidebar.title("Filters")
if not df_sessions.empty:
    min_d, max_d = df_sessions['start_ts'].dt.date.min(), df_sessions['start_ts'].dt.date.max()
else:
    min_d, max_d = datetime.now().date()-timedelta(days=30), datetime.now().date()
date_range = st.sidebar.date_input("Session Date Range", value=(min_d,max_d))

show_graph = st.sidebar.checkbox("2D Knowledge Graph", True)
show_timeline = st.sidebar.checkbox("Session Timeline", True)
show_decay = st.sidebar.checkbox("Memory Decay", True)
show_radar = st.sidebar.checkbox("Focus Radar", True)
show_heatmap = st.sidebar.checkbox("Concept Co-occurrence", True)

# ----------------------------
# KPI cards
# ----------------------------
st.markdown("## 🔑 Key Metrics")
if not df_sessions.empty:
    mask = (df_sessions['start_ts'].dt.date>=date_range[0]) & (df_sessions['start_ts'].dt.date<=date_range[1])
    df_f = df_sessions[mask]
else: df_f=pd.DataFrame()

cols = st.columns(5)
total_hours = df_f['duration_min'].sum()/60 if not df_f.empty else 0
avg_session = df_f['duration_min'].mean() if not df_f.empty else 0
num_sessions = len(df_f)
unique_apps = df_f['app_name'].nunique() if not df_f.empty else 0
unique_concepts = df_decay['keyword'].nunique() if not df_decay.empty else 0

for col, val, lbl in zip(cols,[total_hours, avg_session, num_sessions, unique_apps, unique_concepts],
                         ["Total Hours","Avg Session (min)","Sessions","Active Apps","Concepts"]):
    col.markdown(f"<div class='kpi'><h3>{val:.2f}</h3><small>{lbl}</small></div>",unsafe_allow_html=True)

st.divider()

# ----------------------------
# Timeline
# ----------------------------
if show_timeline:
    st.markdown("## ⏱ Sessions Timeline")
    if df_f.empty:
        st.info("No sessions in selected range")
    else:
        daily = df_f.groupby(df_f['start_ts'].dt.date)['duration_min'].sum().reset_index()
        daily['hours'] = daily['duration_min']/60
        fig = px.area(daily,x='start_ts',y='hours',title="Daily Focus Hours",color_discrete_sequence=['#e43f5a'])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig,use_container_width=True)

# ----------------------------
# Focus radar chart (top apps)
# ----------------------------
if show_radar and not df_f.empty:
    st.markdown("## 🎯 Focus Radar")
    top_apps = df_f.groupby('app_name')['duration_min'].sum().sort_values(ascending=False).head(6)
    labels = top_apps.index.tolist()
    values = (top_apps.values/60).tolist()
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values+[values[0]],theta=labels+[labels[0]],fill='toself',line=dict(color='#00b7c2')))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True)),showlegend=False)
    st.plotly_chart(fig,use_container_width=True)

# ----------------------------
# 2D Knowledge graph
# ----------------------------
if show_graph:
    st.markdown("## 🕸 2D Knowledge Graph")
    try:
        sync_db_to_graph()
        G = get_graph()
        nodes = list(G.nodes())
        edges = [tuple(e) for e in G.edges()]
        pos = graph_layout(nodes, edges)
        # Edge traces
        edge_x,edge_y=[],[]
        for a,b in edges:
            x0,y0=pos[a];x1,y1=pos[b]
            edge_x+=[x0,x1,None]; edge_y+=[y0,y1,None]
        # Node traces
        node_x=[pos[n][0] for n in nodes]
        node_y=[pos[n][1] for n in nodes]
        node_size=[8+20*float(G.nodes[n].get('memory_score',0.3)) for n in nodes]
        node_text=[f"{n}<br>memory:{G.nodes[n].get('memory_score',0.3):.2f}" for n in nodes]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=edge_x,y=edge_y,mode='lines',line=dict(width=1,color='rgba(255,255,255,0.15)'),hoverinfo='none'))
        fig.add_trace(go.Scatter(x=node_x,y=node_y,mode='markers+text',
                                 marker=dict(size=node_size,color=[G.nodes[n].get('memory_score',0.3) for n in nodes],
                                             colorscale='Viridis',showscale=True,colorbar=dict(title='Memory')),
                                 text=[str(n) for n in nodes],textposition='top center',
                                 hoverinfo='text',hovertext=node_text))
        fig.update_layout(showlegend=False,xaxis=dict(visible=False),yaxis=dict(visible=False),
                          paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig,use_container_width=True)
    except Exception as e:
        st.warning(f"KG load failed: {e}")

# ----------------------------
# Memory decay
# ----------------------------
if show_decay:
    st.markdown("## 🧠 Memory Decay")
    if not df_decay.empty:
        latest = df_decay.sort_values('updated_at').groupby('keyword').tail(1)
        fig = px.bar(latest,x='keyword',y='predicted_recall',color='predicted_recall',
                     color_continuous_scale='Viridis',title='Latest Predicted Recall')
        fig.update_layout(xaxis_tickangle=-45,height=400)
        st.plotly_chart(fig,use_container_width=True)

# ----------------------------
# Co-occurrence heatmap
# ----------------------------
if show_heatmap and not df_logs.empty:
    st.markdown("## 🔗 Concept Co-occurrence")
    pairs=[]
    for k in df_logs['ocr_keywords'].head(2000):
        keys=parse_ocr_keywords(k)[:10]
        for i in range(len(keys)):
            for j in range(i+1,len(keys)):
                pairs.append((keys[i],keys[j]))
    if pairs:
        co_df=pd.DataFrame(pairs,columns=['a','b'])
        mat=co_df.groupby(['a','b']).size().unstack(fill_value=0)
        if not mat.empty:
            fig=px.imshow(mat,labels=dict(x='B',y='A',color='co-occurrence'),color_continuous_scale='Viridis')
            st.plotly_chart(fig,use_container_width=True)

st.markdown("---")
st.caption("Offline stats-rich tracker dashboard. All features lightweight and self-contained.")
