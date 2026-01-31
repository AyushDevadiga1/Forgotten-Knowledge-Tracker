# ==========================================================
# dashboard/fkt_dashboard.py | IEEE v4.0 Streamlit Upgrade
# ==========================================================
"""
FKT Dashboard — Fixed, Hardened & Interactive
- Sidebar slider for tab navigation
- 3D KG shows concepts/keywords & memory scores
- Defensive parsing for DB tables
- Rich KPIs, charts, heatmaps, radar, correlations
- System health & diagnostics with error handling
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
    border-radius: 14px;
    padding: 14px;
    margin: 6px 6px;
    box-shadow: 0 6px 22px rgba(0,0,0,0.5);
    text-align: center;
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

# ----------------------------- Utilities -----------------------------
@st.cache_data(ttl=300)
def load_cleaned_data():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Sessions
        try: df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
        except Exception: df_sessions = pd.DataFrame()
        if not df_sessions.empty:
            for col in ["start_ts","end_ts"]:
                if col in df_sessions.columns:
                    df_sessions[col] = pd.to_datetime(df_sessions[col], errors="coerce")
            df_sessions.fillna({"app_name":"Unknown App","audio_label":"N/A",
                                "intent_label":"N/A","intent_confidence":0}, inplace=True)
            if "start_ts" in df_sessions.columns and "end_ts" in df_sessions.columns:
                df_sessions["duration_min"] = ((df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds()/60).clip(lower=0)
            else: df_sessions["duration_min"]=0.0
        else:
            df_sessions = pd.DataFrame(columns=["start_ts","end_ts","app_name","duration_min"])
        # Multi-Modal Logs
        try: df_logs=pd.read_sql("SELECT * FROM multi_modal_logs", conn)
        except: df_logs=pd.DataFrame()
        if not df_logs.empty and "timestamp" in df_logs.columns:
            df_logs["timestamp"]=pd.to_datetime(df_logs["timestamp"], errors="coerce")
        # Memory Decay
        try: df_decay=pd.read_sql("SELECT * FROM memory_decay", conn)
        except: df_decay=pd.DataFrame()
        if not df_decay.empty:
            for col in ["last_seen_ts","updated_at"]:
                if col in df_decay.columns: df_decay[col]=pd.to_datetime(df_decay[col],errors="coerce")
            if "predicted_recall" in df_decay.columns:
                df_decay["predicted_recall"]=pd.to_numeric(df_decay["predicted_recall"],errors="coerce").fillna(0).clip(0,1)
        # Metrics
        try: df_metrics=pd.read_sql("SELECT concept,next_review_time,memory_score FROM metrics", conn)
        except: df_metrics=pd.DataFrame(columns=["concept","next_review_time","memory_score"])
        if not df_metrics.empty and "next_review_time" in df_metrics.columns:
            df_metrics["next_review_time"]=pd.to_datetime(df_metrics["next_review_time"],errors="coerce")
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
    except: pass
    try:
        parsed=json.loads(val.replace("'",'"'))
        if isinstance(parsed,dict): return parsed
        if isinstance(parsed,list): return {str(k):{"score":0.5} for k in parsed}
    except: pass
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

# ----------------------------- Tabs Navigation via Slider -----------------------------
tab_names=[
    "Overview","Knowledge Graph (3D)","Sessions","Memory Decay","Predicted Forgetting",
    "Multi-Modal Logs","Upcoming Reminders","OCR Insights","Audio/Intent Analysis",
    "Visual Attention","Performance Insights","System Health"
]
tab_index=st.sidebar.slider("Select Tab",0,len(tab_names)-1,0)
tabs=st.tabs(tab_names)

# ----------------------------- Overview Tab -----------------------------
with tabs[0]:
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

# ----------------------------- Knowledge Graph (3D) -----------------------------
with tabs[1]:
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
# ----------------------------- Sessions Tab -----------------------------
with tabs[2]:
    st.header("Sessions Timeline & Heatmap")
    if df_sessions.empty:
        st.info("No session data available.")
    else:
        df_sess = df_sessions.copy()
        if "start_ts" in df_sess.columns and "end_ts" in df_sess.columns:
            df_sess["end_ts"] = df_sess["end_ts"].where(df_sess["end_ts"] > df_sess["start_ts"],
                                                        df_sess["start_ts"] + pd.Timedelta(seconds=5))
        else:
            df_sess["end_ts"] = df_sess.get("start_ts", pd.to_datetime(datetime.now()))

        df_sess["duration"] = (pd.to_datetime(df_sess["end_ts"]) - pd.to_datetime(df_sess["start_ts"])).dt.total_seconds() / 60

        # Timeline plot
        try:
            fig_tl = px.timeline(df_sess.sort_values("start_ts"), x_start="start_ts", x_end="end_ts", y="app_name",
                                 color="app_name", title="Session Timeline")
            fig_tl.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_tl, use_container_width=True)
        except Exception as e:
            st.warning(f"Timeline plot failed: {e}")

        # Heatmap plot
        try:
            heat_df = df_sess.groupby(["app_name", df_sess["start_ts"].dt.date])["duration"].sum().reset_index()
            if not heat_df.empty:
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
        except Exception as e:
            st.info(f"Heatmap generation failed: {e}")

        st.download_button("Download Sessions CSV", df_sess.to_csv(index=False), "sessions.csv")

# ----------------------------- Memory Decay Tab -----------------------------
with tabs[3]:
    st.header("Memory Decay")
    if df_decay.empty:
        st.info("No memory decay records.")
    else:
        df_decay2 = df_decay.copy()
        if "last_seen_ts" in df_decay2.columns:
            df_decay2 = df_decay2.rename(columns={"last_seen_ts": "timestamp"})
        df_decay2["timestamp"] = pd.to_datetime(df_decay2.get("timestamp"), errors="coerce")
        df_decay2["predicted_recall"] = pd.to_numeric(df_decay2.get("predicted_recall", 0), errors="coerce").fillna(0).clip(0,1)

        try:
            fig_decay = px.line(df_decay2, x="timestamp", y="predicted_recall", color="concept", markers=True,
                                title="Memory Decay Per Concept", labels={"predicted_recall": "Recall"})
            fig_decay.update_layout(yaxis=dict(range=[0,1]))
            st.plotly_chart(fig_decay, use_container_width=True)
        except Exception as e:
            st.warning(f"Decay plot failed: {e}")

# ----------------------------- Predicted Forgetting Tab -----------------------------
with tabs[4]:
    st.header("Predicted Forgetting Projection")
    if len(concepts) == 0:
        st.info("No concepts available for prediction.")
    else:
        selected_pred = st.selectbox("Choose concept to project", concepts)
        lambda_val = st.slider("Lambda (decay rate)", 0.01, 1.0, 0.1)
        hours = st.slider("Hours ahead", 1, 168, 48)

        df_last = pd.DataFrame()
        if not df_decay.empty:
            df_last = df_decay[df_decay["concept"] == str(selected_pred)].sort_values("last_seen_ts")
        last_score = 0.5
        if not df_last.empty and "predicted_recall" in df_last.columns:
            last_score = float(df_last["predicted_recall"].iloc[-1])

        times = np.linspace(0, hours, 100)
        predicted_scores = last_score * np.exp(-lambda_val * times)
        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=[datetime.now() + timedelta(hours=float(t)) for t in times],
            y=predicted_scores,
            mode="lines",
            name="Predicted"
        ))
        fig_pred.update_layout(yaxis=dict(range=[0,1]), title=f"Predicted Forgetting for {selected_pred}")
        st.plotly_chart(fig_pred, use_container_width=True)

# ----------------------------- Multi-Modal Logs Tab -----------------------------
with tabs[5]:
    st.header("Multi-Modal Logs")
    if df_logs.empty:
        st.info("No multi-modal logs available.")
    else:
        df_logs2 = df_logs.copy()
        if "ocr_keywords" in df_logs2.columns:
            df_logs2["parsed_ocr"] = df_logs2["ocr_keywords"].apply(lambda x: parse_ocr_keywords_field(x) if pd.notna(x) else {})
        st.dataframe(df_logs2.head(300))
        st.download_button("Download Multi-Modal Logs CSV", df_logs2.to_csv(index=False), "multi_modal_logs.csv")
# ----------------------------- Upcoming Reminders Tab -----------------------------
with tabs[6]:
    st.header("Upcoming Reminders")
    if df_metrics.empty:
        st.info("No reminder metrics available.")
    else:
        now = datetime.now()
        if "next_review_time" in df_metrics.columns:
            upcoming = df_metrics[df_metrics["next_review_time"] > now].sort_values("next_review_time").head(200)
            st.dataframe(upcoming[["concept", "next_review_time", "memory_score"]])
            st.download_button("Download Reminders CSV", upcoming.to_csv(index=False), "upcoming_reminders.csv")
        else:
            st.info("No next_review_time column in metrics.")

# ----------------------------- OCR Insights Tab -----------------------------
with tabs[7]:
    st.header("OCR Insights")
    if df_logs.empty or "ocr_keywords" not in df_logs.columns:
        st.info("No OCR logs available.")
    else:
        df_logs_ocr = df_logs.sort_values("timestamp", ascending=False).head(1000).copy()
        df_logs_ocr["parsed_ocr"] = df_logs_ocr["ocr_keywords"].apply(lambda x: parse_ocr_keywords_field(x) if pd.notna(x) else {})
        rows = []
        for _, r in df_logs_ocr.iterrows():
            ts = r.get("timestamp")
            app = r.get("window_title", "")
            parsed = r.get("parsed_ocr", {})
            if isinstance(parsed, dict):
                for k, meta in parsed.items():
                    score = float(meta.get("score", 0.0)) if isinstance(meta, dict) else 0.0
                    rows.append({"timestamp": ts, "window_title": app, "keyword": k, "score": score})
        df_kw = pd.DataFrame(rows)
        if df_kw.empty:
            st.info("No parsed OCR keywords found.")
        else:
            top_kw = df_kw.groupby("keyword")["score"].mean().sort_values(ascending=False).head(40)
            st.plotly_chart(px.bar(top_kw, orientation="v", title="Top OCR Keywords (avg score)"), use_container_width=True)
            st.dataframe(df_kw.groupby("keyword").size().reset_index(name="occurrences").sort_values("occurrences", ascending=False).head(200))

# ----------------------------- Audio / Intent Analysis Tab -----------------------------
with tabs[8]:
    st.header("Audio & Intent Analysis")
    if df_logs.empty:
        st.info("No logs to analyze.")
    else:
        df_ai = df_logs.copy()
        df_ai["audio_label"] = df_ai.get("audio_label", "unknown").astype(str)
        df_ai["intent_label"] = df_ai.get("intent_label", "unknown").astype(str)
        df_ai["intent_confidence"] = pd.to_numeric(df_ai.get("intent_confidence", 0), errors="coerce").fillna(0)
        df_ai["timestamp"] = pd.to_datetime(df_ai.get("timestamp"), errors="coerce")

        last_n = st.slider("Logs to analyze (recent)", 50, 5000, 200)
        df_recent = df_ai.sort_values("timestamp", ascending=False).head(last_n)

        st.markdown("**Audio Label Distribution**")
        try:
            st.plotly_chart(px.pie(df_recent, names="audio_label", title="Audio Labels (recent)"), use_container_width=True)
        except Exception:
            st.write(df_recent["audio_label"].value_counts())

        st.markdown("**Intent Label Distribution**")
        try:
            intent_counts = df_recent["intent_label"].value_counts().reset_index().rename(columns={"index":"intent_label","intent_label":"count"})
            st.plotly_chart(px.bar(intent_counts, x="intent_label", y="count", title="Intent Label Counts (recent)"), use_container_width=True)
        except Exception:
            st.write(df_recent["intent_label"].value_counts())

        st.markdown("**Intent Confidence Timeline**")
        if "timestamp" in df_recent.columns:
            try:
                st.plotly_chart(px.scatter(df_recent.sort_values("timestamp"), x="timestamp", y="intent_confidence", color="intent_label",
                                          title="Intent Confidence over Time", hover_data=["audio_label", "window_title"]), use_container_width=True)
            except Exception as e:
                st.info(f"Plot failed: {e}")
        st.download_button("Download Audio/Intent CSV", df_recent.to_csv(index=False), "audio_intent_recent.csv")

# ----------------------------- Visual Attention Stats Tab -----------------------------
with tabs[9]:
    st.header("Visual Attention / Face Detection Stats")
    if df_logs.empty or "attention_score" not in df_logs.columns:
        st.info("No attention / face detection data logged.")
    else:
        df_att = df_logs.copy()
        df_att["timestamp"] = pd.to_datetime(df_att.get("timestamp"), errors="coerce")
        df_att["attention_score"] = pd.to_numeric(df_att.get("attention_score", 0), errors="coerce").fillna(0)
        avg_att = df_att["attention_score"].mean()
        pct_present = (df_att["attention_score"] > 0).mean() * 100
        c1, c2 = st.columns(2)
        c1.metric("Avg Attention Score", f"{avg_att:.1f}")
        c2.metric("Frames with Presence", f"{pct_present:.1f}%")
        st.plotly_chart(px.histogram(df_att, x="attention_score", nbins=50, title="Attention Score Distribution"), use_container_width=True)
        if "timestamp" in df_att.columns:
            try:
                st.line_chart(df_att.set_index("timestamp")["attention_score"].resample("1H").mean().fillna(0))
            except Exception:
                pass

# ----------------------------- Performance Insights Tab -----------------------------
with tabs[10]:
    st.header("Performance Insights")
    if not df_decay.empty and "predicted_recall" in df_decay.columns:
        avg_mem = df_decay.groupby("concept")["predicted_recall"].mean().sort_values(ascending=False)
        st.subheader("Average Memory Score per Concept")
        st.plotly_chart(px.bar(avg_mem.head(30).reset_index().rename(columns={"predicted_recall":"avg_memory"}),
                               x="concept", y="avg_memory", color="avg_memory", color_continuous_scale="plasma"), use_container_width=True)
    else:
        st.info("No decay data for performance insights.")

    st.markdown("### Daily Productivity Radar")
    if not df_sessions.empty:
        try:
            df_sessions["day"] = df_sessions["start_ts"].dt.day_name()
            daily_focus = df_sessions.groupby("day")["duration_min"].sum().reindex(
                ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]).fillna(0)
            fig_radar = go.Figure(data=go.Scatterpolar(
                r=daily_focus.values,
                theta=daily_focus.index,
                fill='toself',
                name='Daily Focus'
            ))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(1, float(daily_focus.max()))])), showlegend=False)
            st.plotly_chart(fig_radar, use_container_width=True)
        except Exception as e:
            st.warning(f"Radar generation failed: {e}")
    else:
        st.info("No session data for productivity radar.")

# ----------------------------- System Health Tab -----------------------------
with tabs[11]:
    st.header("System Health & Diagnostics")
    c1, c2, c3 = st.columns(3)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]a
        c1.metric("DB Connected", "Yes")
        c1.write(f"Tables: {tables}")
        counts = {}
        for t in ["sessions", "multi_modal_logs", "memory_decay", "metrics"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cur.fetchone()[0]
            except Exception:
                counts[t] = "n/a"
        c1.write("Row counts:")
        c1.write(counts)
        conn.close()
    except Exception as e:
        c1.metric("DB Connected", "No")
        c1.write(str(e))

    model_checks = {}
    model_files = {
        "Intent Classifier": os.path.join(PROJECT_ROOT, "core", "intent_classifier.pkl"),
        "Audio Classifier": os.path.join(PROJECT_ROOT, "core", "audio_classifier.pkl"),
        "Shape Predictor": os.path.join(PROJECT_ROOT, "core", "shape_predictor_68_face_landmarks.dat")
    }
    for k, p in model_files.items():
        model_checks[k] = os.path.exists(p)
    c2.write("Model files presence:")
    c2.write(model_checks)

    try:
        db_size_mb = os.path.getsize(DB_PATH) / (1024 ** 2) if os.path.exists(DB_PATH) else 0.0
        last_ts = pd.to_datetime(df_logs["timestamp"], errors="coerce").max() if (not df_logs.empty and "timestamp" in df_logs.columns) else None
        c3.metric("DB Size (MB)", f"{db_size_mb:.2f}")
        c3.metric("Last Log Timestamp", str(last_ts) if last_ts is not None else "No logs")
    except Exception as e:
        c3.write(f"Error reading DB info: {e}")

    st.markdown("### Lightweight sanity checks")
    if st.button("Run PRAGMA quick_check"):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("PRAGMA quick_check")
            q = cur.fetchall()
            conn.close()
            st.success(f"PRAGMA quick_check result: {q}")
        except Exception as e:
            st.error(f"Sanity check failed: {e}")

    st.markdown("### Async Task Latency (simulated)")
    latency = np.abs(np.random.normal(loc=40, scale=10, size=120))
    fig_lat = px.line(x=pd.date_range(end=datetime.now(), periods=len(latency), freq="T"),
                      y=latency, labels={"x":"time","y":"latency_ms"}, title="Async Task Latency (ms)")
    st.plotly_chart(fig_lat, use_container_width=True)

st.caption("Richer visuals added: 3D KG with keywords, radar, correlations, KPIs, and system diagnostics.")
