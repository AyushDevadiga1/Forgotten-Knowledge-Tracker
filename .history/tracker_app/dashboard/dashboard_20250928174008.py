# -----------------------------
# Fully Enhanced FKT Dashboard (All-in-One)
# -----------------------------
import sys, os, io
import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import sqlite3
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# Set project paths
# -----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from core.knowledge_graph import get_graph, sync_db_to_graph
from config import DB_PATH

# -----------------------------
# Sidebar Settings
# -----------------------------
st.sidebar.title("Settings")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Graph Design Settings:**")
node_min_size = st.sidebar.slider("Min Node Size", 100, 500, 200)
node_max_size = st.sidebar.slider("Max Node Size", 500, 2000, 800)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.1, 1.0, 0.5)

# -----------------------------
# Page Title
# -----------------------------
st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Visualize your learning sessions, memory scores, and knowledge graph in real-time.")

# -----------------------------
# Sync Knowledge Graph
# -----------------------------
with st.spinner("Syncing knowledge graph..."):
    try:
        sync_db_to_graph()
        G = get_graph()
    except Exception as e:
        st.error(f"Error syncing knowledge graph: {e}")
        G = nx.Graph()

# -----------------------------
# Knowledge Graph Section
# -----------------------------
st.subheader("📚 Knowledge Graph Concepts")
if len(G.nodes) == 0:
    st.warning("Knowledge graph is empty. Run the tracker first!")
else:
    table_data = []
    for node in G.nodes:
        mem_score = G.nodes[node].get('memory_score', 0.3)
        next_review = G.nodes[node].get('next_review_time', "N/A")
        table_data.append({
            "Concept": node,
            "Memory Score": round(mem_score, 2),
            "Next Review": next_review
        })
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)

    # Knowledge Graph Visualization
    st.subheader("🕸️ Knowledge Graph Visualization")
    memory_scores = [G.nodes[n].get('memory_score', 0.3) for n in G.nodes]
    cmap = cm.viridis
    norm = mcolors.Normalize(vmin=0, vmax=1)
    node_colors = [cmap(norm(score)) for score in memory_scores]
    node_sizes = [node_min_size + (node_max_size - node_min_size) * score for score in memory_scores]

    fig, ax = plt.subplots(figsize=(12, 10))
    pos = nx.spring_layout(G, seed=42, k=0.8)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)
    nx.draw_networkx_edges(G, pos, alpha=edge_alpha, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=10, ax=ax)
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, label="Memory Score")
    st.pyplot(fig)

    # Memory Scores Progress Bars
    st.subheader("📊 Memory Scores Overview")
    for node in G.nodes:
        mem_score = G.nodes[node].get('memory_score', 0.3)
        st.markdown(f"**{node}:** {mem_score:.2f}")
        st.progress(mem_score)

# -----------------------------
# Session Timeline Section
# -----------------------------
st.subheader("⏱️ Session Timeline")
try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT start_ts, end_ts, app_name FROM sessions ORDER BY start_ts DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()

    if len(rows) == 0:
        st.warning("No session data found. Using fallback demo data.")
        rows = [
            (datetime.now()-timedelta(minutes=30), datetime.now(), "Demo App"),
            (datetime.now()-timedelta(minutes=60), datetime.now()-timedelta(minutes=30), "Demo App 2")
        ]

    session_df = pd.DataFrame(rows, columns=["Start","End","App"])
    session_df["Start"] = pd.to_datetime(session_df["Start"], errors='coerce')
    session_df["End"] = pd.to_datetime(session_df["End"], errors='coerce')
    session_df = session_df.dropna(subset=["Start","End"])
    session_df["Duration_min"] = (session_df["End"] - session_df["Start"]).dt.total_seconds()/60

    # Timeline
    fig2 = px.timeline(session_df, x_start="Start", x_end="End", y="App", color="App", hover_data=["Duration_min"])
    fig2.update_yaxes(autorange="reversed")
    st.plotly_chart(fig2, use_container_width=True)

    # Heatmap
    heatmap_df = session_df.groupby([session_df["App"], session_df["Start"].dt.date])["Duration_min"].sum().reset_index()
    heatmap_pivot = heatmap_df.pivot(index="App", columns="Start", values="Duration_min").fillna(0)
    fig3 = go.Figure(go.Heatmap(
        z=heatmap_pivot.values,
        x=[str(d) for d in heatmap_pivot.columns],
        y=heatmap_pivot.index,
        colorscale="Viridis",
        hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} mins<extra></extra>"
    ))
    fig3.update_layout(title="App Usage Heatmap (Minutes)", xaxis_title="Date", yaxis_title="App")
    st.plotly_chart(fig3, use_container_width=True)

except sqlite3.OperationalError as e:
    st.error(f"Database error: {e}")

# -----------------------------
# Learning Analytics & Additional Charts
# -----------------------------
st.subheader("📈 Learning Analytics")

# --- Fallback / Dynamic Data ---
try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Focus & Retention Trend
    c.execute("SELECT start_ts, focus_score, retention_score FROM focus_retention ORDER BY start_ts DESC LIMIT 50")
    fr_rows = c.fetchall()
    if not fr_rows:
        hours = list(range(24))
        focus_scores = [0.5]*24
        retention_scores = [50]*24
    else:
        df_fr = pd.DataFrame(fr_rows, columns=["Start","Focus","Retention"])
        df_fr["Hour"] = pd.to_datetime(df_fr["Start"]).dt.hour
        hours = df_fr["Hour"].tolist()
        focus_scores = df_fr["Focus"].tolist()
        retention_scores = df_fr["Retention"].tolist()
    
    # Memory Analytics per Topic
    c.execute("SELECT topic, reviewed_count, forgotten_count FROM memory_analytics")
    mem_rows = c.fetchall()
    if not mem_rows:
        topics = ["Demo"]
        reviewed = [1]
        forgotten = [0]
    else:
        df_mem = pd.DataFrame(mem_rows, columns=["Topic","Reviewed","Forgotten"])
        topics = df_mem["Topic"].tolist()
        reviewed = df_mem["Reviewed"].tolist()
        forgotten = df_mem["Forgotten"].tolist()
    
    # Topic Retention
    c.execute("SELECT topic, retention_percentage FROM topic_retention")
    tr_rows = c.fetchall()
    if not tr_rows:
        topic_retention = [50]*len(topics)
    else:
        df_tr = pd.DataFrame(tr_rows, columns=["Topic","Retention"])
        topic_retention = df_tr["Retention"].tolist()
    
    # Keyword Analytics
    c.execute("SELECT keyword, frequency, trend FROM keyword_stats")
    kw_rows = c.fetchall()
    if not kw_rows:
        keywords = ["Demo"]
        freq = [1]
        trend = [1]
    else:
        df_kw = pd.DataFrame(kw_rows, columns=["Keyword","Frequency","Trend"])
        keywords = df_kw["Keyword"].tolist()
        freq = df_kw["Frequency"].tolist()
        trend = df_kw["Trend"].tolist()
    
    conn.close()
except:
    hours = list(range(24))
    focus_scores = [0.5]*24
    retention_scores = [50]*24
    topics = ["Demo"]
    reviewed = [1]
    forgotten = [0]
    topic_retention = [50]
    keywords = ["Demo"]
    freq = [1]
    trend = [1]

# --- Focus & Retention Trend ---
fig_focus = px.line(x=hours, y=focus_scores, labels={"x":"Hour","y":"Focus Score"}, title="Focus Trend")
fig_retention = px.line(x=hours, y=retention_scores, labels={"x":"Hour","y":"Retention %"}, title="Retention Trend")
st.plotly_chart(fig_focus, use_container_width=True)
st.plotly_chart(fig_retention, use_container_width=True)

# --- Memory Analytics ---
fig_memory = go.Figure()
fig_memory.add_trace(go.Bar(x=topics, y=reviewed, name="Reviewed", marker_color='green'))
fig_memory.add_trace(go.Bar(x=topics, y=forgotten, name="Forgotten", marker_color='red'))
fig_memory.update_layout(barmode='group', title="Memory Analytics per Topic")
st.plotly_chart(fig_memory, use_container_width=True)

# --- Topic Retention ---
fig_topic_retention = px.line(x=topics, y=topic_retention, labels={"x":"Topic","y":"Retention %"}, title="Topic Retention")
st.plotly_chart(fig_topic_retention, use_container_width=True)

# --- Keyword Analytics ---
fig_keywords = go.Figure()
fig_keywords.add_trace(go.Bar(x=keywords, y=freq, name="Frequency", marker_color='#36a2eb'))
fig_keywords.add_trace(go.Scatter(x=keywords, y=trend, name="Trend", marker_color='#9c27b0'))
fig_keywords.update_layout(title="Top OCR Keywords & Trends")
st.plotly_chart(fig_keywords, use_container_width=True)

# -----------------------------
# Knowledge Log Table
# -----------------------------
st.subheader("📖 Knowledge Log")
try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT start_ts, topic, app_name, duration_min, retention_pct FROM knowledge_log ORDER BY start_ts DESC LIMIT 10")
    log_rows = c.fetchall()
    conn.close()

    if not log_rows:
        log_rows = [(datetime.now(), "Demo Topic", "Demo App", 10, 80)]

    log_df = pd.DataFrame(log_rows, columns=["Time","Topic","App","Duration (min)","Retention (%)"])
    st.dataframe(log_df, use_container_width=True)
except:
    st.warning("Knowledge log data unavailable.")

# -----------------------------
# Upcoming Reminders
# -----------------------------
st.subheader("⏰ Upcoming Reminders")
reminders = ["Math Review", "OCR Test", "Physics Practice"]
st.write("\n".join(f"- {r}" for r in reminders))
