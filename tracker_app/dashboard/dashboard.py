#dashboard/dashboard.py
'''     Make sure after loading the 3d graph wait for few seconds as we are
    loading a lot of nodes in the 3d graph at once .
    Please reload or Comment out the 3d Graph tab if error persisits as 
    there are a lot of calculation,operations and resources allocated to it.
'''
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

# Fix font warnings in matplotlib
plt.rcParams['font.sans-serif'] = ['Arial']

# Project Root
PROJECT_ROOT = r"C:\Users\hp\Desktop\FKT\tracker_app"
sys.path.append(PROJECT_ROOT)

from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Content Filtering & Cleanup
# -----------------------------
# Common garbage/noise words and patterns to filter
GARBAGE_KEYWORDS = {
    'unknown', 'n/a', 'none', 'null', 'error', 'failed', 'loading', 'please wait',
    'click here', 'advertisement', 'ads', 'banner', 'popup', 'cookie', 'notification',
    'untitled', 'unnamed', 'temp', 'tmp', 'debug', 'test', 'sample', 'demo',
    'silence', 'noise', 'background', 'static', 'empty', 'blank'
}

# Low-confidence threshold (0-1 scale)
CONFIDENCE_THRESHOLD = 0.3
MIN_FREQUENCY = 2  # Minimum occurrences to be relevant
MIN_SESSION_DURATION = 0.5  # Minimum 30 seconds

def is_relevant_content(keyword, confidence=1.0, frequency=1):
    """Check if content is relevant and not garbage"""
    if not keyword:
        return False
    
    keyword_clean = str(keyword).lower().strip()
    
    # Check against garbage list
    if keyword_clean in GARBAGE_KEYWORDS:
        return False
    
    # Check for low confidence
    if confidence < CONFIDENCE_THRESHOLD:
        return False
    
    # Check for sufficient frequency
    if frequency < MIN_FREQUENCY:
        return False
    
    # Filter very short or very long keywords (likely noise)
    if len(keyword_clean) < 2 or len(keyword_clean) > 100:
        return False
    
    # Filter common noise patterns
    if keyword_clean.count('_') > 3 or keyword_clean.count('?') > 0:
        return False
    
    return True

def clean_text(text):
    """Normalize and clean text data"""
    if not text:
        return ""
    text = str(text).lower().strip()
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

def filter_dataframe_by_relevance(df, column, confidence_col=None, freq_threshold=1):
    """Filter dataframe to keep only relevant content"""
    if df.empty:
        return df
    
    # Remove None/null/N/A values
    df = df[df[column].notna()]
    df = df[df[column] != '']
    
    # Clean text
    df[column] = df[column].apply(clean_text)
    
    # Remove garbage keywords
    df = df[~df[column].isin(GARBAGE_KEYWORDS)]
    
    # Filter by confidence if provided
    if confidence_col and confidence_col in df.columns:
        df = df[df[confidence_col] >= CONFIDENCE_THRESHOLD]
    
    # Filter short/malformed entries
    df = df[df[column].str.len() >= 2]
    df = df[df[column].str.len() <= 100]
    
    return df

# -----------------------------
# Utility: Load & Clean Data
# -----------------------------
def load_cleaned_data():
    conn = sqlite3.connect(DB_PATH)
    
    # Sessions
    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    df_sessions["start_ts"] = pd.to_datetime(df_sessions["start_ts"], errors='coerce')
    df_sessions["end_ts"] = pd.to_datetime(df_sessions["end_ts"], errors='coerce')
    df_sessions["app_name"] = df_sessions["app_name"].fillna("Unknown App")
    df_sessions["audio_label"] = df_sessions["audio_label"].fillna("N/A")
    df_sessions["intent_label"] = df_sessions["intent_label"].fillna("N/A")
    df_sessions["intent_confidence"] = pd.to_numeric(df_sessions["intent_confidence"], errors='coerce').fillna(0)
    df_sessions["duration_min"] = (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60

    # Filter sessions: remove garbage and low-confidence
    df_sessions = df_sessions[df_sessions["duration_min"] >= MIN_SESSION_DURATION]  # Remove very short sessions
    df_sessions = filter_dataframe_by_relevance(df_sessions, "app_name")
    df_sessions = filter_dataframe_by_relevance(df_sessions, "audio_label")
    df_sessions = filter_dataframe_by_relevance(df_sessions, "intent_label")
    df_sessions = df_sessions[df_sessions["intent_confidence"] > CONFIDENCE_THRESHOLD]

    # Multi-Modal Logs
    df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"], errors='coerce')
    if "ocr_keywords" in df_logs.columns:
        df_logs = filter_dataframe_by_relevance(df_logs, "ocr_keywords")
        df_logs.rename(columns={"ocr_keywords": "keyword"}, inplace=True)
    else:
        df_logs["keyword"] = ""

    # Memory Decay - filter by relevance
    df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
    df_decay["last_seen_ts"] = pd.to_datetime(df_decay["last_seen_ts"], errors='coerce')
    df_decay["updated_at"] = pd.to_datetime(df_decay["updated_at"], errors='coerce')
    if "keyword" in df_decay.columns:
        df_decay = filter_dataframe_by_relevance(df_decay, "keyword")
        # Additional filter: only keep concepts with decent memory score
        df_decay = df_decay[df_decay["predicted_recall"] > 0.1]
    else:
        df_decay = pd.DataFrame()

    # Metrics / Reminders
    df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
    df_metrics["next_review_time"] = pd.to_datetime(df_metrics["next_review_time"], errors='coerce')
    if "concept" in df_metrics.columns:
        df_metrics = filter_dataframe_by_relevance(df_metrics, "concept")
        df_metrics = df_metrics[df_metrics["memory_score"] > 0.1]  # Filter low scores
    else:
        df_metrics = pd.DataFrame()

    conn.close()
    return df_sessions, df_logs, df_decay, df_metrics

df_sessions, df_logs, df_decay, df_metrics = load_cleaned_data()

# -----------------------------
# Streamlit Page Setup
# -----------------------------
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide")
st.title("🔮 Forgotten Knowledge Tracker Dashboard")
st.markdown("Visualize your learning sessions, memory scores, knowledge graph, upcoming reminders, and more.")

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
# Overview Tab
# -----------------------------
with tabs[0]:
    st.subheader("📊 Dashboard Overview")
    df_sessions_filtered = df_sessions.dropna(subset=["start_ts","end_ts"])
    total_hours = df_sessions_filtered["duration_min"].sum() / 60 if not df_sessions_filtered.empty else 0
    avg_session = df_sessions_filtered["duration_min"].mean() if not df_sessions_filtered.empty else 0
    num_sessions = len(df_sessions_filtered)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Hours", f"{total_hours:.2f} h")
    col2.metric("Avg Session", f"{avg_session:.1f} min")
    col3.metric("Number of Sessions", f"{num_sessions}")

    if not df_sessions_filtered.empty:
        daily_hours = df_sessions_filtered.groupby(df_sessions_filtered["start_ts"].dt.date)["duration_min"].sum() / 60
        col4.line_chart(daily_hours, height=100)

# -----------------------------
# Knowledge Graph Tab
# -----------------------------
with tabs[1]:
    st.subheader("🕸️ Knowledge Graph (Filtered)")
    sync_db_to_graph()
    G = get_graph()
    
    if G.nodes:
        # Filter out low-value nodes
        nodes_to_remove = []
        for node in G.nodes():
            memory_score = G.nodes[node].get('memory_score', 0.3)
            frequency = G.degree(node)
            
            # Remove isolated or low-memory nodes
            if memory_score < 0.15 or (frequency < 2 and memory_score < 0.3):
                nodes_to_remove.append(node)
        
        # Remove garbage nodes
        for node in nodes_to_remove:
            G.remove_node(node)
        
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
            
            st.markdown(f"**Showing {len(G.nodes)} relevant concepts** (filtered from all data)")
            st.pyplot(fig)
        else:
            st.info("No relevant concepts after filtering.")
    else:
        st.info("Knowledge graph empty.")

# -----------------------------
# 3D Knowledge Graph Tab
# -----------------------------
with tabs[2]:
    st.subheader("🧩 3D Knowledge Graph (Intent → Keywords, Filtered)")
    
    # Build 3D Graph from DB with filtering
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get intents with minimum confidence
    cursor.execute("""
        SELECT DISTINCT intent_label FROM sessions 
        WHERE intent_label IS NOT NULL 
        AND intent_confidence > ?
    """, (CONFIDENCE_THRESHOLD,))
    intents = [row[0] for row in cursor.fetchall()]
    
    # Filter garbage intents
    intents = [i for i in intents if is_relevant_content(i)]

    edges = []
    nodes = set()
    edge_count = {}
    
    for intent in intents:
        # Get keywords with minimum occurrence
        cursor.execute("""
            SELECT DISTINCT audio_label FROM sessions 
            WHERE intent_label=? 
            AND audio_label IS NOT NULL 
            AND audio_label != 'N/A'
            AND intent_confidence > ?
        """, (intent, CONFIDENCE_THRESHOLD))
        keywords = [row[0] for row in cursor.fetchall()]
        
        # Filter garbage keywords
        keywords = [k for k in keywords if is_relevant_content(k)]
        
        for kw in keywords:
            edge = (intent, kw)
            edges.append(edge)
            edge_count[edge] = edge_count.get(edge, 0) + 1
            nodes.add(intent)
            nodes.add(kw)
    
    conn.close()

    if edges and nodes:
        # Filter edges with sufficient frequency
        edges = [e for e in edges if edge_count[e] >= 2]
        
        if edges:
            G3d = nx.Graph()
            G3d.add_edges_from(edges)
            pos_3d = nx.spring_layout(G3d, dim=3, seed=42)

            x_nodes = [pos_3d[n][0] for n in G3d.nodes()]
            y_nodes = [pos_3d[n][1] for n in G3d.nodes()]
            z_nodes = [pos_3d[n][2] for n in G3d.nodes()]
            labels = list(G3d.nodes())

            edge_x = []
            edge_y = []
            edge_z = []

            for edge in G3d.edges():
                x0, y0, z0 = pos_3d[edge[0]]
                x1, y1, z1 = pos_3d[edge[1]]
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]
                edge_z += [z0, z1, None]

            fig_3d = go.Figure()

            fig_3d.add_trace(go.Scatter3d(
                x=edge_x, y=edge_y, z=edge_z,
                mode='lines',
                line=dict(color='black', width=2),
                hoverinfo='none'
            ))

            fig_3d.add_trace(go.Scatter3d(
                x=x_nodes, y=y_nodes, z=z_nodes,
                mode='markers+text',
                marker=dict(size=8, color='orange'),
                text=labels,
                textposition='top center'
            ))

            fig_3d.update_layout(
                scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z'),
                height=700,
                title=f"3D Knowledge Graph: {len(G3d.nodes)} Concepts, {len(G3d.edges)} Connections (Filtered)"
            )
            st.plotly_chart(fig_3d, use_container_width=True)
        else:
            st.info("No relevant intent-keyword connections after filtering.")
    else:
        st.info("No intents or keywords found in DB.")

# -----------------------------
# Sessions Tab
# -----------------------------
with tabs[3]:
    st.subheader("⏱️ Session Timeline & Heatmap")
    if not df_sessions_filtered.empty:
        df_sess = df_sessions_filtered.copy()
        df_sess["end_ts"] = df_sess["end_ts"].where(df_sess["end_ts"] > df_sess["start_ts"], df_sess["start_ts"] + pd.Timedelta(seconds=5))
        df_sess["duration"] = (df_sess["end_ts"] - df_sess["start_ts"]).dt.total_seconds()/60

        fig_tl = px.timeline(df_sess, x_start="start_ts", x_end="end_ts", y="app_name", color="app_name")
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
        fig_hm.update_layout(title="App Usage Duration Heatmap")
        st.plotly_chart(fig_hm, use_container_width=True)

# -----------------------------
# Memory Decay Tab
# -----------------------------
with tabs[4]:
    st.subheader("📉 Memory Decay Curves (Filtered)")

    if not df_decay.empty:
        # Get top concepts by relevance
        top_keywords = df_decay.groupby("keyword").agg({
            "predicted_recall": "mean",
            "keyword": "count"
        }).rename(columns={"keyword": "frequency"}).reset_index(drop=True)
        top_keywords = top_keywords.nlargest(15, "predicted_recall")
        
        df_decay_filtered = df_decay[df_decay["keyword"].isin(top_keywords.index)]
        
        if not df_decay_filtered.empty:
            fig_decay = px.line(df_decay_filtered, x="last_seen_ts", y="predicted_recall", color="keyword", markers=True,
                                title="Memory Decay Per Concept (Top Relevant)", labels={"last_seen_ts":"Time","predicted_recall":"Recall"})
            fig_decay.update_layout(yaxis=dict(range=[0,1]))
            st.markdown(f"**Showing {len(df_decay_filtered['keyword'].unique())} relevant concepts**")
            st.plotly_chart(fig_decay, use_container_width=True)
        else:
            st.info("No relevant decay data after filtering.")
    else:
        st.info("No memory decay data found.")

# -----------------------------
# Predicted Forgetting Tab
# -----------------------------
with tabs[5]:
    st.subheader("📈 Predicted Forgetting Overlay")
    
    if not df_decay.empty:
        # Filter to relevant concepts
        relevant_concepts = df_decay[df_decay["predicted_recall"] > 0.2]["keyword"].unique()
        
        if len(relevant_concepts) > 0:
            selected_pred = st.selectbox("Choose concept", sorted(relevant_concepts))
            lambda_val = 0.1
            hours = 24
            df_last = df_decay[df_decay["keyword"]==selected_pred]
            last_score = df_last["predicted_recall"].iloc[-1] if not df_last.empty else 0.5
            times = np.linspace(0, hours, 50)
            predicted_scores = last_score * np.exp(-lambda_val * times)

            fig_pred = go.Figure()
            fig_pred.add_trace(go.Scatter(
                x=[datetime.now() + timedelta(hours=t) for t in times],
                y=predicted_scores,
                mode="lines",
                name="Predicted Recall"
            ))
            fig_pred.update_layout(yaxis=dict(range=[0,1]), xaxis_title="Time", yaxis_title="Memory Score",
                                   title=f"Predicted Forgetting Curve for {selected_pred}")
            st.plotly_chart(fig_pred, use_container_width=True)
        else:
            st.info("No relevant concepts for prediction (all have low memory scores).")
    else:
        st.info("No decay data for prediction.")

# -----------------------------
# Multi-Modal Logs Tab
# -----------------------------
with tabs[6]:
    st.subheader("🎤 Multi-Modal Logs (Filtered)")
    if not df_logs.empty:
        # Show stats before filtering
        total_logs = len(df_logs)
        
        # Get top keywords
        keyword_freq = df_logs["keyword"].value_counts().head(20)
        
        st.markdown(f"**Total relevant logs: {len(df_logs)} of {total_logs}**")
        st.markdown(f"**Top keywords (by frequency):**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Bar chart of top keywords
            fig_kw = px.bar(keyword_freq, title="Top Keywords", labels={"value": "Frequency", "index": "Keyword"})
            st.plotly_chart(fig_kw, use_container_width=True)
        
        with col2:
            # Pie chart of distribution
            st.metric("Unique Keywords", len(df_logs["keyword"].unique()))
            st.metric("Total Occurrences", len(df_logs))
        
        # Show filtered data
        st.dataframe(df_logs.head(50))
    else:
        st.info("No relevant multi-modal logs available.")

# -----------------------------
# Upcoming Reminders Tab
# -----------------------------
with tabs[7]:
    st.subheader("⏰ Upcoming Reminders (Filtered)")
    now = datetime.now()
    
    if not df_metrics.empty:
        # Filter upcoming reminders with good memory scores
        upcoming = df_metrics[
            (df_metrics["next_review_time"] > now) & 
            (df_metrics["memory_score"] > 0.1)
        ].sort_values("next_review_time").head(20)
        
        if not upcoming.empty:
            st.markdown(f"**{len(upcoming)} concepts due for review (from {len(df_metrics)} total)**")
            
            # Show priority concepts
            col1, col2 = st.columns(2)
            
            with col1:
                # Upcoming timeline
                upcoming_display = upcoming[["concept", "next_review_time", "memory_score"]].copy()
                upcoming_display["memory_score"] = upcoming_display["memory_score"].round(2)
                st.dataframe(upcoming_display)
            
            with col2:
                # Memory score distribution
                fig_mem = px.histogram(upcoming, x="memory_score", nbins=10, title="Memory Score Distribution")
                st.plotly_chart(fig_mem, use_container_width=True)
        else:
            st.info("No upcoming reminders with sufficient memory score.")
    else:
        st.info("No reminders data available.")
