# ==============================================================
# dashboard/dashboard_modern_full.py — FKT Dashboard vNext
# ==============================================================
import sys, os, sqlite3, time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Project Root
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
st.set_page_config(page_title="FKT Dashboard", layout="wide", page_icon="🔮")
st.markdown("<h1 style='text-align:center; color:#4B0082;'>🔮 Forgotten Knowledge Tracker</h1>", unsafe_allow_html=True)
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

    # KPI Cards
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
# 2D Knowledge Graph Tab
# -----------------------------
with tabs[1]:
    st.subheader("🕸️ Knowledge Graph")
    sync_db_to_graph()
    G = get_graph()
    if G.nodes:
        memory_scores = [G.nodes[n].get('memory_score',0.3) for n in G.nodes]
        node_sizes = [node_min_size + (node_max_size-node_min_size)*score for score in memory_scores]
        node_colors = memory_scores

        pos = nx.spring_layout(G, seed=42, k=0.8)
        edge_x, edge_y = [], []
        for e in G.edges():
            x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
            edge_x += [x0, x1, None]; edge_y += [y0, y1, None]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines',
                                 line=dict(width=1,color='rgba(100,100,100,0.5)'), hoverinfo='none'))
        node_x = [pos[n][0] for n in G.nodes]
        node_y = [pos[n][1] for n in G.nodes]
        fig.add_trace(go.Scatter(x=node_x, y=node_y, mode='markers+text',
                                 text=list(G.nodes), textposition='top center',
                                 marker=dict(size=node_sizes, color=node_colors,
                                             colorscale='Viridis',
                                             colorbar=dict(title="Memory Score"),
                                             line=dict(width=2,color='DarkSlateGrey'))))
        fig.update_layout(title="2D Knowledge Graph", showlegend=False, height=700)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Knowledge graph empty.")

# -----------------------------
# 3D Knowledge Graph Tab
# -----------------------------
with tabs[2]:
    st.subheader("🧩 3D Knowledge Graph")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT intent_label FROM sessions WHERE intent_label IS NOT NULL")
    intents = [row[0] for row in cursor.fetchall()]
    edges, nodes = [], set()
    for intent in intents:
        cursor.execute("SELECT DISTINCT audio_label || '_' || rowid FROM sessions WHERE intent_label=?",(intent,))
        kws = [r[0] for r in cursor.fetchall()]
        for kw in kws: edges.append((intent,kw)); nodes.update([intent,kw])
    conn.close()
    
    if edges:
        G3d = nx.Graph(); G3d.add_edges_from(edges)
        pos3d = nx.spring_layout(G3d, dim=3, seed=42, k=0.8)
        x_nodes=[pos3d[n][0] for n in G3d.nodes()]; y_nodes=[pos3d[n][1] for n in G3d.nodes()]
        z_nodes=[pos3d[n][2] for n in G3d.nodes()]; labels=list(G3d.nodes())
        edge_x,edge_y,edge_z=[],[],[]
        for e in G3d.edges():
            x0,y0,z0=pos3d[e[0]]; x1,y1,z1=pos3d[e[1]]
            edge_x+=[x0,x1,None]; edge_y+=[y0,y1,None]; edge_z+=[z0,z1,None]
        fig3d=go.Figure()
        fig3d.add_trace(go.Scatter3d(x=edge_x,y=edge_y,z=edge_z,mode='lines',
                                     line=dict(color='gray',width=2),hoverinfo='none'))
        fig3d.add_trace(go.Scatter3d(x=x_nodes,y=y_nodes,z=z_nodes,mode='markers+text',
                                     text=labels,textposition='top center',
                                     marker=dict(size=8,color='orange',line=dict(width=1,color='black'))))
        fig3d.update_layout(scene=dict(xaxis_title='X',yaxis_title='Y',zaxis_title='Z'),
                            height=750,title="3D Knowledge Graph",margin=dict(l=0,r=0,b=0,t=50))
        with st.spinner("Rendering 3D graph..."):
            time.sleep(2)
        st.plotly_chart(fig3d,use_container_width=True)
    else:
        st.info("No intents or keywords found.")

# -----------------------------
# Sessions Tab
# -----------------------------
with tabs[3]:
    st.subheader("⏱️ Sessions")
    if not df_sessions_filtered.empty:
        df_sess=df_sessions_filtered.copy()
        df_sess["end_ts"]=df_sess["end_ts"].where(df_sess["end_ts"]>df_sess["start_ts"], df_sess["start_ts"]+pd.Timedelta(seconds=5))
        df_sess["duration"]=(df_sess["end_ts"]-df_sess["start_ts"]).dt.total_seconds()/60

        fig_tl=px.timeline(df_sess,x_start="start_ts",x_end="end_ts",y="app_name",
                           color="app_name",hover_data=["audio_label","intent_label"])
        fig_tl.update_yaxes(autorange="reversed")
        fig_tl.update_layout(title="Session Timeline", height=500)
        st.plotly_chart(fig_tl,use_container_width=True)

        heat_df=df_sess.groupby(["app_name",df_sess["start_ts"].dt.date])["duration"].sum().reset_index()
        heat_pivot=heat_df.pivot(index="app_name",columns="start_ts",values="duration").fillna(0)
        fig_hm=go.Figure(data=go.Heatmap(
            z=heat_pivot.values,
            x=[str(d) for d in heat_pivot.columns],
            y=heat_pivot.index,
            colorscale="Viridis",
            hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} min<extra></extra>"
        ))
        fig_hm.update_layout(title="App Usage Heatmap", height=500)
        st.plotly_chart(fig_hm,use_container_width=True)
    else:
        st.info("No session data.")

# -----------------------------
# Memory Decay Radar
# -----------------------------
with tabs[4]:
    st.subheader("📉 Memory Decay")
    if not df_decay.empty:
        latest_decay=df_decay.groupby("keyword")["predicted_recall"].last()
        fig_radar=go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=latest_decay.values,
            theta=latest_decay.index,
            fill='toself',
            name='Current Recall',
            line=dict(color='orange')
        ))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,1])),
                                title="Concept Recall Radar Chart")
        st.plotly_chart(fig_radar,use_container_width=True,height=500)
    else:
        st.info("No decay data.")

# -----------------------------
# Predicted Forgetting
# -----------------------------
with tabs[5]:
    st.subheader("📈 Predicted Forgetting")
    if not df_decay.empty:
        selected_pred=st.selectbox("Choose concept",df_decay["keyword"].unique())
        last_score=df_decay[df_decay["keyword"]==selected_pred]["predicted_recall"].iloc[-1]
        times=np.linspace(0,24,50)
        predicted_scores=last_score*np.exp(-0.1*times)
        fig_pred=go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=[datetime.now()+timedelta(hours=t) for t in times],
            y=predicted_scores,
            mode='lines+markers',
            line=dict(color='orange',width=3),
            marker=dict(size=6)
        ))
        fig_pred.update_layout(yaxis=dict(range=[0,1]),xaxis_title="Time",yaxis_title="Memory Score",
                               title=f"Predicted Forgetting Curve for {selected_pred}",height=500)
        st.plotly_chart(fig_pred,use_container_width=True)
    else:
        st.info("No decay data for prediction.")

# -----------------------------
# Multi-Modal Logs
# -----------------------------
with tabs[6]:
    st.subheader("🎤 Multi-Modal Logs")
    if not df_logs.empty:
        st.dataframe(df_logs.head(100))
        filter_app=st.text_input("Filter by audio_label/app_name","")
        if filter_app:
            filtered=df_logs[df_logs["audio_label"].str.contains(filter_app,case=False,na=False)]
            st.dataframe(filtered)
    else:
        st.info("No logs available.")

# -----------------------------
# Upcoming Reminders
# -----------------------------
with tabs[7]:
    st.subheader("⏰ Upcoming Reminders")
    upcoming=df_metrics[df_metrics["next_review_time"]>datetime.now()].sort_values("next_review_time").head(20)
    if not upcoming.empty:
        for _,r in upcoming.iterrows():
            st.markdown(f"""
                <div style='border-radius:10px; background-color:#E6E6FA; padding:15px; margin-bottom:8px;'>
                    <h4 style='color:#4B0082;'>{r['concept']}</h4>
                    <p>Next Review: <b>{r['next_review_time']}</b> | Memory Score: <b>{r['memory_score']:.2f}</b></p>
                </div>
            """,unsafe_allow_html=True)
    else:
        st.info("No upcoming reminders.")
