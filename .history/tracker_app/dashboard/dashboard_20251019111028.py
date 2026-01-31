# dashboard/new_dashboard_part1.py
import sys, os, sqlite3
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.cm as cm             # for colormaps
import matplotlib.colors as mcolors    # for color normalization
import matplotlib.pyplot as plt        # if you use matplotlib plots somewhere
import networkx as nx                  # knowledge graph handling
import plotly.express as px            # Plotly Express charts
import plotly.graph_objects as go      # Plotly GO charts
import worldcloud 

# Add project root
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Streamlit Page Config
# -----------------------------
st.set_page_config(
    page_title="FKT Tracker Dashboard", layout="wide"
)
st.markdown("""
<style>
body {background-color: #0e1117; color: #e6eef3;}
h1, h2, h3, h4, h5 {color:#8be9fd;}
.stButton>button {background-color:#282c34;color:#cdeacb;border-radius:6px;}
.stDataFrame th {background-color:#181c22;color:#8be9fd;}
.stDataFrame td {background-color:#0e1117;color:#cdeacb;}
</style>
""", unsafe_allow_html=True)
st.title("🔮 Forgotten Knowledge Tracker — Next-Gen Dashboard")

# -----------------------------
# DB Loading with caching
# -----------------------------
@st.cache_data(ttl=300)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Sessions
        df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
        df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors="coerce")
        df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors="coerce")
        df_sessions["duration_min"] = ((df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds()/60).clip(lower=0)
        df_sessions["app_name"].fillna("Unknown App", inplace=True)
        df_sessions["intent_label"].fillna("N/A", inplace=True)
        df_sessions["audio_label"].fillna("N/A", inplace=True)

        # Memory decay
        df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
        for col in ["last_seen_ts","updated_at"]:
            if col in df_decay.columns:
                df_decay[col] = pd.to_datetime(df_decay[col], errors="coerce")

        # Metrics
        df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
        if "next_review_time" in df_metrics.columns:
            df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors="coerce")

        # Multi-modal logs
        df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
        if "timestamp" in df_logs.columns:
            df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors="coerce")

        return df_sessions, df_decay, df_metrics, df_logs
    finally:
        conn.close()

df_sessions, df_decay, df_metrics, df_logs = load_data()

# -----------------------------
# Sync Knowledge Graph
# -----------------------------
try:
    sync_db_to_graph()
    G = get_graph()
except Exception:
    G = None

st.success("✅ Data Loaded and Knowledge Graph Synced")
# -----------------------------
# Sidebar Filters & Controls
# -----------------------------
st.sidebar.header("Tracker Controls")
camera_on = st.sidebar.checkbox("Enable Webcam", value=False)
audio_on = st.sidebar.checkbox("Enable Audio", value=True)
screenshot_on = st.sidebar.checkbox("Enable Screenshots", value=True)
st.sidebar.markdown("---")

st.sidebar.subheader("Graph Visual Settings")
node_min_size = st.sidebar.slider("Min Node Size", 50, 800, 120)
node_max_size = st.sidebar.slider("Max Node Size", 200, 3000, 700)
edge_alpha = st.sidebar.slider("Edge Transparency", 0.05, 1.0, 0.45)

st.sidebar.subheader("Data Filters")
date_range = st.sidebar.date_input(
    "Filter Sessions by Date Range",
    [datetime.now() - timedelta(days=30), datetime.now()]
)
selected_apps = st.sidebar.multiselect(
    "Filter Apps", options=df_sessions["app_name"].unique(), default=list(df_sessions["app_name"].unique())
)

# -----------------------------
# Apply Filters
# -----------------------------
df_sessions_filtered = df_sessions[
    (df_sessions["start_ts"].dt.date >= date_range[0]) &
    (df_sessions["start_ts"].dt.date <= date_range[1]) &
    (df_sessions["app_name"].isin(selected_apps))
] if not df_sessions.empty else pd.DataFrame()

# -----------------------------
# KPI Cards
# -----------------------------
def card_html(title, value, subtitle=""):
    return f"""
    <div style="
        background: linear-gradient(160deg, rgba(22,27,34,0.85), rgba(10,12,16,0.6));
        border-radius: 12px;
        padding: 14px;
        margin:6px;
        text-align:center;
        box-shadow: 0 6px 22px rgba(0,0,0,0.5);">
        <h4 style="color:#8be9fd;margin:0;">{title}</h4>
        <p style="color:#cdeacb;margin:0;font-size:18px;font-weight:600;">{value}</p>
        <div style="color:#8da3b3;font-size:12px;">{subtitle}</div>
    </div>
    """

total_hours = df_sessions_filtered["duration_min"].sum()/60 if not df_sessions_filtered.empty else 0
avg_session = df_sessions_filtered["duration_min"].mean() if not df_sessions_filtered.empty else 0
num_sessions = len(df_sessions_filtered)
unique_concepts = len(G.nodes) if G else 0
avg_mem_score = round(np.mean([G.nodes[n].get("memory_score",0.3) for n in G.nodes]),2) if G else 0
upcoming_reminders = len(df_metrics[df_metrics["next_review_time"]>datetime.now()]) if not df_metrics.empty else 0

cols = st.columns(6)
cols[0].markdown(card_html("Total Hours", f"{total_hours:.2f} h", "Across filtered sessions"), unsafe_allow_html=True)
cols[1].markdown(card_html("Avg Session", f"{avg_session:.1f} min", "Mean session duration"), unsafe_allow_html=True)
cols[2].markdown(card_html("Sessions", f"{num_sessions}", "Total sessions loaded"), unsafe_allow_html=True)
cols[3].markdown(card_html("Unique Concepts", f"{unique_concepts}", "Knowledge graph nodes"), unsafe_allow_html=True)
cols[4].markdown(card_html("Avg Memory Score", f"{avg_mem_score:.2f}", "Across all concepts"), unsafe_allow_html=True)
cols[5].markdown(card_html("Upcoming Reminders", f"{upcoming_reminders}", "Next review events"), unsafe_allow_html=True)

st.markdown("---")

# -----------------------------
# Tabs / Slider Navigation
# -----------------------------
tab_names = [
    "Overview","Knowledge Graph","3D KG","Sessions","Memory Decay","Predicted Forgetting",
    "Multi-Modal Logs","Upcoming Reminders","OCR Insights","Audio / Intent Analysis",
    "Visual Attention Stats","Performance Insights","System Health"
]

tabs = st.tabs(tab_names)
# ================================
# Part 3: Tab Content
# ================================

# -----------------------------
# Overview Tab
# -----------------------------
with tabs[0]:
    st.subheader("📊 Dashboard Overview")
    
    if not df_sessions_filtered.empty:
        # Daily session duration
        daily_hours = df_sessions_filtered.groupby(df_sessions_filtered["start_ts"].dt.date)["duration_min"].sum()/60
        fig_daily = px.line(daily_hours, labels={"index":"Date","value":"Hours"}, title="Daily Learning Hours")
        st.plotly_chart(fig_daily, use_container_width=True)

        # Top Apps
        top_apps = df_sessions_filtered.groupby("app_name")["duration_min"].sum().sort_values(ascending=False).head(10)
        fig_apps = px.bar(top_apps, x=top_apps.index, y=top_apps.values, labels={"x":"App","y":"Hours"}, title="Top Apps Usage")
        st.plotly_chart(fig_apps, use_container_width=True)
        
        # Memory Score Distribution
        if G and G.nodes:
            mem_scores = [G.nodes[n].get("memory_score",0.3) for n in G.nodes]
            fig_mem = px.histogram(mem_scores, nbins=20, labels={"value":"Memory Score"}, title="Memory Score Distribution")
            st.plotly_chart(fig_mem, use_container_width=True)
    else:
        st.info("No session data in the selected date range.")

# -----------------------------
# Knowledge Graph (2D) Tab
# -----------------------------
with tabs[1]:
    st.subheader("🕸️ Knowledge Graph (2D)")
    sync_db_to_graph()
    G = get_graph()
    
    if G.nodes:
        memory_scores = [G.nodes[n].get("memory_score",0.3) for n in G.nodes]
        cmap = cm.plasma
        norm = mcolors.Normalize(vmin=0,vmax=1)
        node_colors = [cmap(norm(s)) for s in memory_scores]
        node_sizes = [node_min_size + (node_max_size - node_min_size) * s for s in memory_scores]
        
        fig, ax = plt.subplots(figsize=(12,10))
        pos = nx.spring_layout(G, seed=42, k=0.5)
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)
        nx.draw_networkx_edges(G, pos, alpha=edge_alpha, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=10, ax=ax)
        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        fig.colorbar(sm, ax=ax, label="Memory Score")
        st.pyplot(fig)
    else:
        st.info("Knowledge graph is empty.")

# -----------------------------
# 3D Knowledge Graph Tab
# -----------------------------
with tabs[2]:
    st.subheader("🧩 3D Knowledge Graph (Intent → Keywords)")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT intent_label FROM sessions WHERE intent_label IS NOT NULL")
    intents = [row[0] for row in cursor.fetchall()]
    
    edges = []
    nodes = set()
    for intent in intents:
        cursor.execute("SELECT DISTINCT audio_label || '_' || rowid FROM sessions WHERE intent_label=?", (intent,))
        kws = [row[0] for row in cursor.fetchall()]
        for kw in kws:
            edges.append((intent, kw))
            nodes.add(intent)
            nodes.add(kw)
    conn.close()
    
    if edges:
        G3d = nx.Graph()
        G3d.add_edges_from(edges)
        pos_3d = nx.spring_layout(G3d, dim=3, seed=42)
        
        x_nodes = [pos_3d[n][0] for n in G3d.nodes()]
        y_nodes = [pos_3d[n][1] for n in G3d.nodes()]
        z_nodes = [pos_3d[n][2] for n in G3d.nodes()]
        labels = list(G3d.nodes())
        
        edge_x, edge_y, edge_z = [], [], []
        for e in G3d.edges():
            x0,y0,z0 = pos_3d[e[0]]
            x1,y1,z1 = pos_3d[e[1]]
            edge_x += [x0,x1,None]
            edge_y += [y0,y1,None]
            edge_z += [z0,z1,None]
        
        fig_3d = go.Figure()
        fig_3d.add_trace(go.Scatter3d(x=edge_x, y=edge_y, z=edge_z, mode='lines', line=dict(color='black', width=2), hoverinfo='none'))
        fig_3d.add_trace(go.Scatter3d(
            x=x_nodes, y=y_nodes, z=z_nodes, mode='markers+text',
            marker=dict(size=8,color='orange'),
            text=labels, textposition='top center'
        ))
        fig_3d.update_layout(
            scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z'),
            height=700, title="3D Knowledge Graph"
        )
        st.plotly_chart(fig_3d, use_container_width=True)
    else:
        st.info("No intents or keywords found in DB.")

# -----------------------------
# Sessions Tab
# -----------------------------
with tabs[3]:
    st.subheader("⏱️ Sessions Timeline & Heatmap")
    if not df_sessions_filtered.empty:
        df_sess = df_sessions_filtered.copy()
        df_sess["end_ts"] = df_sess["end_ts"].where(df_sess["end_ts"] > df_sess["start_ts"], df_sess["start_ts"] + pd.Timedelta(seconds=5))
        df_sess["duration"] = (df_sess["end_ts"] - df_sess["start_ts"]).dt.total_seconds()/60
        
        # Timeline
        fig_tl = px.timeline(df_sess, x_start="start_ts", x_end="end_ts", y="app_name", color="app_name", title="Session Timeline")
        fig_tl.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_tl, use_container_width=True)
        
        # Heatmap
        heat_df = df_sess.groupby(["app_name", df_sess["start_ts"].dt.date])["duration"].sum().reset_index()
        heat_pivot = heat_df.pivot(index="app_name", columns="start_ts", values="duration").fillna(0)
        fig_hm = go.Figure(data=go.Heatmap(
            z=heat_pivot.values,
            x=[str(d) for d in heat_pivot.columns],
            y=heat_pivot.index,
            colorscale="Viridis",
            hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} min<extra></extra>"
        ))
        fig_hm.update_layout(title="App Usage Heatmap")
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.info("No session data available for selected filters.")

# -----------------------------
# Memory Decay Tab
# -----------------------------
with tabs[4]:
    st.subheader("📉 Memory Decay Curves")
    if not df_decay.empty:
        selected_keywords = st.multiselect("Select Concepts", df_decay["keyword"].unique(), default=df_decay["keyword"].unique()[:5])
        df_plot = df_decay[df_decay["keyword"].isin(selected_keywords)]
        fig_decay = px.line(df_plot, x="last_seen_ts", y="predicted_recall", color="keyword", markers=True,
                            title="Memory Decay Over Time")
        fig_decay.update_layout(yaxis=dict(range=[0,1]), xaxis_title="Time", yaxis_title="Recall Score")
        st.plotly_chart(fig_decay, use_container_width=True)
    else:
        st.info("No memory decay data available.")

# -----------------------------
# Predicted Forgetting Tab
# -----------------------------
with tabs[5]:
    st.subheader("📈 Predicted Forgetting Curves")
    if not df_decay.empty:
        selected_keyword = st.selectbox("Choose Concept", df_decay["keyword"].unique())
        lambda_val = 0.1
        hours = 24
        df_last = df_decay[df_decay["keyword"]==selected_keyword]
        last_score = df_last["predicted_recall"].iloc[-1] if not df_last.empty else 0.5
        times = np.linspace(0,hours,50)
        predicted_scores = last_score*np.exp(-lambda_val*times)
        
        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=[datetime.now() + timedelta(hours=t) for t in times],
            y=predicted_scores, mode="lines", name="Predicted Recall"
        ))
        fig_pred.update_layout(title=f"Predicted Forgetting Curve: {selected_keyword}", yaxis=dict(range=[0,1]),
                               xaxis_title="Time", yaxis_title="Memory Score")
        st.plotly_chart(fig_pred, use_container_width=True)
    else:
        st.info("No decay data for prediction.")

# -----------------------------
# Multi-Modal Logs Tab
# -----------------------------
with tabs[6]:
    st.subheader("🎤 Multi-Modal Logs")
    if not df_logs.empty:
        st.dataframe(df_logs.head(200))
        st.download_button("Download Logs CSV", df_logs.to_csv(index=False).encode(), "multi_modal_logs.csv")
    else:
        st.info("No multi-modal logs available.")

# -----------------------------
# Upcoming Reminders Tab
# -----------------------------
with tabs[7]:
    st.subheader("⏰ Upcoming Reminders")
    now = datetime.now()
    upcoming = df_metrics[df_metrics["next_review_time"]>now].sort_values("next_review_time").head(20)
    if not upcoming.empty:
        st.dataframe(upcoming[["concept","next_review_time","memory_score"]])
    else:
        st.info("No upcoming reminders.")
# ================================
# Part 4: Advanced Tabs
# ================================

# -----------------------------
# OCR Insights Tab
# -----------------------------
with tabs[8]:
    st.subheader("📄 OCR Insights & Keywords")
    
    # Assuming OCR keywords stored in multi_modal_logs with column 'ocr_text'
    if "ocr_text" in df_logs.columns:
        df_ocr = df_logs.dropna(subset=["ocr_text"]).copy()
        st.write(f"Total OCR entries: {len(df_ocr)}")
        
        # Top OCR Keywords
        from collections import Counter
        import re
        words = []
        for t in df_ocr["ocr_text"]:
            words += re.findall(r"\w+", str(t).lower())
        top_words = Counter(words).most_common(20)
        df_top_words = pd.DataFrame(top_words, columns=["Keyword","Count"])
        fig_ocr = px.bar(df_top_words, x="Keyword", y="Count", title="Top OCR Keywords")
        st.plotly_chart(fig_ocr, use_container_width=True)
        
        # Wordcloud (optional, lightweight)
        try:
            from wordcloud import WordCloud
            wc = WordCloud(width=800, height=400, background_color="white").generate(" ".join(words))
            st.image(wc.to_array(), use_column_width=True)
        except:
            st.info("WordCloud library not installed. Install `wordcloud` for visual effect.")
    else:
        st.info("No OCR data found in logs.")

# -----------------------------
# Audio / Intent Analysis Tab
# -----------------------------
with tabs[9]:
    st.subheader("🎤 Audio & Intent Metrics")
    
    if not df_sessions.empty:
        # Intent distribution
        intent_counts = df_sessions["intent_label"].value_counts()
        fig_intent = px.pie(values=intent_counts.values, names=intent_counts.index, title="Intent Distribution")
        st.plotly_chart(fig_intent, use_container_width=True)
        
        # Confidence over time
        df_conf = df_sessions.dropna(subset=["intent_confidence"]).copy()
        fig_conf = px.line(df_conf, x="start_ts", y="intent_confidence", color="intent_label",
                           title="Intent Confidence Over Time")
        st.plotly_chart(fig_conf, use_container_width=True)
    else:
        st.info("No session/intent data found.")

# -----------------------------
# Visual Attention Tab
# -----------------------------
with tabs[10]:
    st.subheader("👀 Visual Attention / Face Metrics")
    
    if "attention_score" in df_logs.columns:
        df_attn = df_logs.dropna(subset=["attention_score"])
        st.write(f"Entries with attention scores: {len(df_attn)}")
        
        fig_attn = px.histogram(df_attn, x="attention_score", nbins=20, title="Attention Score Distribution")
        st.plotly_chart(fig_attn, use_container_width=True)
    else:
        st.info("No attention metrics found in logs.")

# -----------------------------
# Performance Insights Tab
# -----------------------------
with tabs[11]:
    st.subheader("🚀 Performance Insights & Correlations")
    
    if not df_decay.empty:
        # Memory correlation heatmap
        df_corr = df_decay.pivot(index="last_seen_ts", columns="keyword", values="predicted_recall").corr()
        fig_corr = px.imshow(df_corr, text_auto=True, aspect="auto", title="Concept Correlation Heatmap")
        st.plotly_chart(fig_corr, use_container_width=True)
        
        # Top memory concepts radar chart
        top_keywords = df_decay.groupby("keyword")["predicted_recall"].mean().sort_values(ascending=False).head(5)
        categories = top_keywords.index.tolist()
        values = top_keywords.values.tolist()
        values += values[:1]  # close loop
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=values, theta=categories + [categories[0]],
                                           fill='toself', name='Average Recall'))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1])), title="Top Concepts Recall Radar")
        st.plotly_chart(fig_radar, use_container_width=True)
    else:
        st.info("No memory decay data to analyze performance.")

# -----------------------------
# System Health Tab
# -----------------------------
with tabs[12]:
    st.subheader("🖥️ System Health & DB Metrics")
    
    # DB connectivity
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        st.success("Database connected successfully!")
        st.write(f"Tables in DB: {tables}")
        
        # Rows per table
        table_counts = {}
        for tbl in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
            table_counts[tbl] = cursor.fetchone()[0]
        st.dataframe(pd.DataFrame(list(table_counts.items()), columns=["Table","Rows"]))
        
        conn.close()
    except Exception as e:
        st.error(f"DB connection failed: {e}")
    
    # Performance metrics
    st.write("Performance Metrics (simulated / placeholders)")
    st.metric("Last Sync Duration", "0.15 s")
    st.metric("Graph Nodes", len(G.nodes) if G else 0)
    st.metric("Graph Edges", len(G.edges) if G else 0)
