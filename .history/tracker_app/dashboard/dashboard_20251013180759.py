# ==========================================================
# dashboard/fkt_dashboard.py | IEEE v4.0 Streamlit Upgrade
# ==========================================================
"""
FKT Dashboard — Slider-Based Tab Navigation (All Tabs)
"""

import sys, os, sqlite3, json, re
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------- Project Root -----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
from config import DB_PATH

# Lazy imports
try:
    from core.knowledge_graph import get_graph, sync_db_to_graph
except Exception:
    get_graph = None
    sync_db_to_graph = None

# ----------------------------- Streamlit Page Setup -----------------------------
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide")
st.markdown("""
<style>
body { background-color: #0b0f14; color: #e6eef3; }
.stApp { background: linear-gradient(180deg,#071014,#0b0f14); }
.metric-card {
    background: linear-gradient(160deg, rgba(22,27,34,0.85), rgba(10,12,16,0.6));
    border-radius: 14px; padding: 14px; margin: 6px 6px;
    box-shadow: 0 6px 22px rgba(0,0,0,0.5); text-align: center;
}
.metric-card h4 { color: #8be9fd; margin:0 0 6px 0; }
.metric-card p { color: #cdeacb; margin:0; font-size:18px; font-weight:600; }
.small-muted { color: #8da3b3; font-size:12px; }
</style>
""", unsafe_allow_html=True)

st.title("🔮 Forgotten Knowledge Tracker — Visual Intelligence Dashboard")
st.markdown("Interactive dashboard for sessions, memory scores, 3D knowledge graph, and system health.")

# ----------------------------- Sidebar Controls -----------------------------
st.sidebar.title("Tracker Controls")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)
st.sidebar.markdown("---")

st.sidebar.subheader("Graph Visual Settings")
node_min_size = st.sidebar.slider("Min Node Size", 10, 800, 120)
node_max_size = st.sidebar.slider("Max Node Size", 50, 3000, 700)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.05, 1.0, 0.45)

st.sidebar.subheader("Data Filters")
date_range = st.sidebar.date_input(
    "Filter Sessions by Date Range",
    value=[(datetime.now() - timedelta(days=30)).date(), datetime.now().date()]
)

tab_names = [
    "Overview","Knowledge Graph (3D)","Sessions","Memory Decay","Predicted Forgetting",
    "Multi-Modal Logs","Upcoming Reminders","OCR Insights","Audio/Intent Analysis",
    "Visual Attention","Performance Insights","System Health"
]
selected_tab_index = st.sidebar.slider("Select Tab", 0, len(tab_names)-1, 0)
selected_tab = tab_names[selected_tab_index]

# ----------------------------- Utilities -----------------------------
@st.cache_data(ttl=300)
def load_cleaned_data():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Sessions
        try: df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
        except: df_sessions = pd.DataFrame()
        if not df_sessions.empty:
            for col in ["start_ts","end_ts"]:
                if col in df_sessions.columns:
                    df_sessions[col] = pd.to_datetime(df_sessions[col], errors="coerce")
            df_sessions.fillna({"app_name":"Unknown App","audio_label":"N/A","intent_label":"N/A","intent_confidence":0}, inplace=True)
            if "start_ts" in df_sessions.columns and "end_ts" in df_sessions.columns:
                df_sessions["duration_min"] = ((df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds()/60).clip(lower=0)
            else: df_sessions["duration_min"] = 0.0
        else: df_sessions = pd.DataFrame(columns=["start_ts","end_ts","app_name","duration_min"])

        # Multi-Modal Logs
        try: df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
        except: df_logs = pd.DataFrame()
        if not df_logs.empty and "timestamp" in df_logs.columns:
            df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors="coerce")

        # Memory Decay
        try: df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
        except: df_decay = pd.DataFrame()
        if not df_decay.empty:
            for col in ["last_seen_ts","updated_at"]:
                if col in df_decay.columns: df_decay[col] = pd.to_datetime(df_decay[col], errors="coerce")
            if "predicted_recall" in df_decay.columns:
                df_decay["predicted_recall"] = pd.to_numeric(df_decay["predicted_recall"], errors="coerce").fillna(0).clip(0,1)

        # Metrics
        try: df_metrics = pd.read_sql("SELECT concept,next_review_time,memory_score FROM metrics", conn)
        except: df_metrics = pd.DataFrame(columns=["concept","next_review_time","memory_score"])
        if not df_metrics.empty and "next_review_time" in df_metrics.columns:
            df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors="coerce")
        return df_sessions, df_logs, df_decay, df_metrics
    finally: conn.close()

def parse_ocr_keywords_field(val):
    if val is None: return {}
    if isinstance(val, dict): return val
    if isinstance(val,(list,tuple)): return {str(x):{"score":0.5} for x in val}
    if not isinstance(val,str):
        try: val=str(val)
        except: return {}
    val=val.strip()
    if val=="": return {}
    try:
        parsed=json.loads(val)
        if isinstance(parsed,dict): return parsed
        if isinstance(parsed,list): return {str(k):{"score":0.5} for k in parsed}
    except: 
        try:
            parsed=json.loads(val.replace("'",'"'))
            if isinstance(parsed,dict): return parsed
            if isinstance(parsed,list): return {str(k):{"score":0.5} for k in parsed}
        except: return {}
    parts=[p.strip() for p in re.split(r"[,\n;]+", val) if p.strip()]
    return {k:{"score":0.5} for k in parts}

# ----------------------------- Load Data -----------------------------
df_sessions, df_logs, df_decay, df_metrics = load_cleaned_data()
if isinstance(date_range,(list,tuple)) and len(date_range)>=2:
    start_date,end_date=date_range[0],date_range[1]
else: start_date=end_date=date_range
if isinstance(start_date,datetime): start_date=start_date.date()
if isinstance(end_date,datetime): end_date=end_date.date()
if not df_sessions.empty and "start_ts" in df_sessions.columns:
    try:
        df_sessions=df_sessions[(df_sessions["start_ts"].dt.date>=start_date)&(df_sessions["start_ts"].dt.date<=end_date)]
    except:
        df_sessions["start_ts"]=pd.to_datetime(df_sessions.get("start_ts"), errors="coerce")
        df_sessions=df_sessions[(df_sessions["start_ts"].dt.date>=start_date)&(df_sessions["start_ts"].dt.date<=end_date)]

# ----------------------------- Load Knowledge Graph -----------------------------
G=nx.Graph()
if sync_db_to_graph is not None and get_graph is not None:
    try:
        sync_db_to_graph()
        G=get_graph() or nx.Graph()
    except: G=nx.Graph()
else:
    try:
        kg_path=os.path.join(PROJECT_ROOT,"data","kg_graph.gpickle")
        if os.path.exists(kg_path): G=nx.read_gpickle(kg_path)
    except: G=nx.Graph()
concepts=list(G.nodes)

# ----------------------------- KPI Cards -----------------------------
def card_html(title,value,subtitle=""):
    return f"<div class='metric-card'><h4>{title}</h4><p>{value}</p><div class='small-muted'>{subtitle}</div></div>"

total_hours=(df_sessions["duration_min"].sum()/60.0) if (not df_sessions.empty and "duration_min" in df_sessions.columns) else 0.0
avg_session=df_sessions["duration_min"].mean() if (not df_sessions.empty and "duration_min" in df_sessions.columns) else 0.0
num_sessions=len(df_sessions) if not df_sessions.empty else 0
unique_concepts=len(concepts)
col1,col2,col3,col4=st.columns([1.2,1.2,1.2,1.2])
col1.markdown(card_html("Total Hours",f"{total_hours:.2f} h","Across filtered sessions"), unsafe_allow_html=True)
col2.markdown(card_html("Avg Session",f"{avg_session:.1f} min","Mean session duration"), unsafe_allow_html=True)
col3.markdown(card_html("Sessions",f"{num_sessions}","Total sessions loaded"), unsafe_allow_html=True)
col4.markdown(card_html("Unique Concepts",f"{unique_concepts}","Nodes in knowledge graph"), unsafe_allow_html=True)
st.markdown("---")

# ----------------------------- Tab Rendering -----------------------------
if selected_tab=="Overview":
    # ----------------------------- Overview Tab -----------------------------
    st.header("Overview")
    st.write("Quick activity and memory score summary.")
    if not df_sessions.empty:
        recent=df_sessions.sort_values("start_ts").tail(200)
        if "start_ts" in recent.columns:
            c1,c2=st.columns([2,1])
            try: c1.line_chart(recent.set_index("start_ts")["duration_min"].rolling(5).mean())
            except: c1.line_chart(recent.set_index("start_ts")["duration_min"].fillna(0))
            c2.metric("Concepts tracked",f"{unique_concepts}")
    else: st.info("No session data available.")
    st.markdown("---")
    st.subheader("Top/Low Memory Concepts")
    if len(G.nodes):
        mem_list=[]
        for n in G.nodes:
            try: mem_list.append({"Concept":n,"Memory Score":float(G.nodes[n].get("memory_score",0.3))})
            except: mem_list.append({"Concept":n,"Memory Score":0.3})
        df_mem=pd.DataFrame(mem_list).sort_values("Memory Score")
        st.dataframe(df_mem.head(30))
    else: st.info("Knowledge graph empty.")

elif selected_tab=="Knowledge Graph (3D)":
    # ----------------------------- Knowledge Graph (3D) -----------------------------
    st.header("Interactive 3D Knowledge Graph")
    if len(G.nodes)==0:
        st.info("Knowledge graph is empty. Sync DB to populate nodes.")
    else:
        try:
            pos2d=nx.spring_layout(G, seed=42, k=0.5, iterations=50)
            centrality=nx.degree_centrality(G)
            nodes=list(G.nodes)
            x,y,z,text,size,color=[],[],[],[],[],[]
            mem_scores=[float(G.nodes.get(n,{}).get("memory_score",0.3)) for n in nodes]
            norm=mcolors.Normalize(vmin=0,vmax=1)
            cmap=cm.plasma
            for i,n in enumerate(nodes):
                px_,py_=pos2d.get(n,(np.random.random(),np.random.random()))
                pz_=float(centrality.get(n,0))*0.8
                x.append(px_); y.append(py_); z.append(pz_)
                ms=float(G.nodes.get(n,{}).get("memory_score",0.3))
                text.append(f"{n}<br>Memory: {ms:.2f}<br>Keywords: {', '.join(G.nodes.get(n,{}).get('keywords',[]))}")
                scaled=node_min_size+(node_max_size-node_min_size)*ms
                size.append(float(max(6,scaled)))
                color.append(mcolors.to_hex(cmap(norm(ms))))
            edge_x,edge_y,edge_z=[],[],[]
            for n1,n2 in G.edges():
                try:
                    edge_x+=[pos2d.get(n1,(0,0))[0],pos2d.get(n2,(0,0))[0],None]
                    edge_y+=[pos2d.get(n1,(0,0))[1],pos2d.get(n2,(0,0))[1],None]
                    edge_z+=[centrality.get(n1,0)*0.8,centrality.get(n2,0)*0.8,None]
                except: continue
            node_trace=go.Scatter3d(
                x=x,y=y,z=z,mode='markers',
                marker=dict(size=[max(6,s/40) for s in size],color=color,opacity=0.9),
                text=[n for n in nodes], hovertext=text, hoverinfo='text'
            )
            edge_trace=go.Scatter3d(
                x=edge_x,y=edge_y,z=edge_z,mode='lines',
                line=dict(width=1,color=f'rgba(150,150,150,{edge_alpha})')
            )
            fig=go.Figure(data=[edge_trace,node_trace])
            fig.update_layout(scene=dict(xaxis=dict(showbackground=False,visible=False),
                                         yaxis=dict(showbackground=False,visible=False),
                                         zaxis=dict(showbackground=False,visible=False)),
                              margin=dict(l=0,r=0,t=30,b=0),
                              showlegend=False, template="plotly_dark")
            st.plotly_chart(fig,use_container_width=True, theme="streamlit")
        except Exception as e:
            st.error(f"Failed to render 3D graph: {e}")

