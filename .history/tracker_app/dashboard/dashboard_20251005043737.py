# dashboard/dashboard.py
import sys
import os
import json
import sqlite3
import streamlit as st
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta


# -----------------------------
# Project Paths
# -----------------------------
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"  # adjust as needed
sys.path.append(PROJECT_ROOT)



from config import DB_PATH
from core.knowledge_graph import get_graph,sync_db_to_graph
# -----------------------------
# Sidebar Settings
# -----------------------------
# dashboard/dashboard.py
import sys
import os
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import json
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Page & Sidebar
# -----------------------------
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide")
st.sidebar.title("Settings")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Graph Settings**")
node_min_size = st.sidebar.slider("Min Node Size", 100, 500, 200)
node_max_size = st.sidebar.slider("Max Node Size", 500, 2000, 800)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.1, 1.0, 0.5)

st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Visualize your learning sessions, memory decay, and knowledge graph in real-time.")

# -----------------------------
# Sync & Load Knowledge Graph
# -----------------------------
sync_db_to_graph()
G = get_graph()

# -----------------------------
# Knowledge Graph Table
# -----------------------------
st.subheader("📚 Knowledge Graph Concepts")
if len(G.nodes) == 0:
    st.warning("Knowledge graph is empty. Run the tracker first!")
else:
    table_data = []
    for node in G.nodes:
        mem_score = G.nodes[node].get('memory_score', 0.3)
        next_review = G.nodes[node].get('next_review_time', "N/A")
        table_data.append({"Concept": node, "Memory Score": round(mem_score, 2), "Next Review": next_review})
    df_graph = pd.DataFrame(table_data)
    st.dataframe(df_graph, use_container_width=True)

# -----------------------------
# Knowledge Graph Visualization
# -----------------------------
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

# -----------------------------
# Memory Scores Progress Bars
# -----------------------------
st.subheader("📊 Memory Scores Overview")
for node in G.nodes:
    mem_score = G.nodes[node].get('memory_score', 0.3)
    st.markdown(f"**{node}:** {mem_score:.2f}")
    st.progress(mem_score)

# -----------------------------
# Session Timeline & App Usage
# -----------------------------
st.subheader("⏱️ Recent Session Timeline & App Usage")
try:
    conn = sqlite3.connect(DB_PATH)
    sessions_df = pd.read_sql("SELECT start_ts, end_ts, app_name FROM sessions ORDER BY start_ts DESC LIMIT 50", conn)
    conn.close()

    if not sessions_df.empty:
        sessions_df["Start"] = pd.to_datetime(sessions_df["start_ts"], errors='coerce')
        sessions_df["End"] = pd.to_datetime(sessions_df["end_ts"], errors='coerce')
        sessions_df = sessions_df.dropna(subset=["Start","End"])
        sessions_df["End"] = sessions_df["End"].where(sessions_df["End"] > sessions_df["Start"], sessions_df["Start"] + pd.Timedelta(seconds=5))
        sessions_df["Duration_min"] = (sessions_df["End"] - sessions_df["Start"]).dt.total_seconds() / 60

        # Timeline Plot
        fig_timeline = px.timeline(
            sessions_df, x_start="Start", x_end="End", y="app_name", color="app_name",
            hover_data=["Start","End"], title="Recent Activity Timeline"
        )
        fig_timeline.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_timeline, use_container_width=True)

        # Total App Usage
        total_hours = sessions_df["Duration_min"].sum()/60
        st.metric("Total App Usage Hours", f"{total_hours:.2f} hrs")

        # App Usage Heatmap
        heatmap_df = sessions_df.groupby(["app_name", sessions_df["Start"].dt.date])["Duration_min"].sum().reset_index()
        heatmap_pivot = heatmap_df.pivot(index="app_name", columns="Start", values="Duration_min").fillna(0)
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=heatmap_pivot.values,
            x=[str(d) for d in heatmap_pivot.columns],
            y=heatmap_pivot.index,
            colorscale="Viridis",
            hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} mins<extra></extra>"
        ))
        fig_heatmap.update_layout(title="App Usage Heatmap (Minutes)", xaxis_title="Date", yaxis_title="App")
        st.plotly_chart(fig_heatmap, use_container_width=True)

    else:
        st.warning("No session data found yet.")

except Exception as e:
    st.warning(f"Error fetching sessions: {e}")

# -----------------------------
# Memory Decay
# -----------------------------
st.subheader("📉 Memory Decay Curves")
def fetch_memory_decay(concept=None):
    conn = sqlite3.connect(DB_PATH)
    if concept:
        df = pd.read_sql("SELECT keyword AS concept, last_seen_ts AS timestamp, predicted_recall AS memory_score FROM memory_decay WHERE keyword = ? ORDER BY last_seen_ts ASC", conn, params=(concept,))
    else:
        df = pd.read_sql("SELECT keyword AS concept, last_seen_ts AS timestamp, predicted_recall AS memory_score FROM memory_decay ORDER BY last_seen_ts ASC", conn)
    conn.close()
    return df

df_decay = fetch_memory_decay()
if not df_decay.empty:
    df_decay["timestamp"] = pd.to_datetime(df_decay["timestamp"], errors='coerce')
    df_decay["memory_score"] = pd.to_numeric(df_decay["memory_score"], errors='coerce')
    fig_decay_all = px.line(df_decay, x="timestamp", y="memory_score", color="concept",
                            markers=True, title="Memory Decay per Concept", labels={"timestamp":"Time","memory_score":"Predicted Recall"})
    fig_decay_all.update_layout(yaxis=dict(range=[0,1]))
    st.plotly_chart(fig_decay_all, use_container_width=True)
else:
    st.warning("No memory decay data found yet.")

# -----------------------------
# Individual Concept Memory Decay
# -----------------------------
st.subheader("🧠 Individual Concept Decay Viewer")
concepts = list(G.nodes)
selected_concepts = st.multiselect("Select concepts", concepts, default=concepts[:3])
if selected_concepts:
    fig_decay = go.Figure()
    for concept in selected_concepts:
        df_c = fetch_memory_decay(concept)
        if not df_c.empty:
            df_c["timestamp"] = pd.to_datetime(df_c["timestamp"], errors='coerce')
            df_c["memory_score"] = pd.to_numeric(df_c["memory_score"], errors='coerce')
            fig_decay.add_trace(go.Scatter(x=df_c["timestamp"], y=df_c["memory_score"], mode='lines+markers', name=concept))
    if fig_decay.data:
        fig_decay.update_layout(title="Memory Decay Over Time", xaxis_title="Time", yaxis_title="Memory Score", yaxis=dict(range=[0,1]))
        st.plotly_chart(fig_decay, use_container_width=True)
    else:
        st.warning("No decay data for selected concepts.")

# -----------------------------
# Predicted Forgetting Curve Overlay
# -----------------------------
st.subheader("📈 Predicted Forgetting Curve Overlay")
def predicted_forgetting_curve(lambda_val=0.1, hours=24, points=50):
    times = np.linspace(0, hours, points)
    scores = np.exp(-lambda_val*times)
    return times, scores

concept = st.selectbox("Choose concept for predicted forgetting", concepts)
if concept:
    times, scores = predicted_forgetting_curve()
    fig_pred = go.Figure()
    fig_pred.add_trace(go.Scatter(
        x=[datetime.now()+timedelta(hours=t) for t in times],
        y=scores,
        mode='lines',
        name=f"Predicted {concept}"
    ))
    fig_pred.update_layout(title=f"Predicted Forgetting Curve for {concept}",
                           xaxis_title="Time", yaxis_title="Predicted Recall", yaxis=dict(range=[0,1]))
    st.plotly_chart(fig_pred, use_container_width=True)

# -----------------------------
# OCR Keyword Trends
# -----------------------------
st.subheader("🔑 OCR Keyword Trends")
df_trends = []
try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT timestamp, ocr_keywords FROM multi_modal_logs ORDER BY timestamp ASC")
    rows = c.fetchall()
    conn.close()

    for row in rows:
        timestamp = pd.to_datetime(row[0])
        kws_raw = row[1]
        try:
            kws = json.loads(kws_raw) if isinstance(kws_raw,str) else kws_raw
        except:
            kws = []
        if isinstance(kws, dict):
            for k in kws.keys():
                df_trends.append({"Keyword": k, "Timestamp": timestamp})
        elif isinstance(kws, list):
            for k in kws:
                df_trends.append({"Keyword": k, "Timestamp": timestamp})
    df_trends = pd.DataFrame(df_trends)

    if not df_trends.empty:
        fig_keywords = px.line(df_trends, x="Timestamp", y="Keyword", markers=True, title="OCR Keyword Trends")
        st.plotly_chart(fig_keywords, use_container_width=True)
except Exception as e:
    st.warning(f"No keyword logs yet: {e}")
