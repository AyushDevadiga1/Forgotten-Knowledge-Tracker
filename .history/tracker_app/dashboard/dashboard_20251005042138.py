# dashboard/dashboard.py
import sys
import os
import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import sqlite3
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from config import DB_PATH
from core.knowledge_graph import get_graph, sync_db_to_graph

# -----------------------------
# Streamlit Page Config
# -----------------------------
st.set_page_config(page_title="Forgotten Knowledge Tracker", layout="wide", initial_sidebar_state="expanded")

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
# Sync Knowledge Graph
# -----------------------------
sync_db_to_graph()
G = get_graph()

# -----------------------------
# Helper Functions
# -----------------------------
def fetch_memory_decay(concept=None):
    conn = sqlite3.connect(DB_PATH)
    if concept:
        query = """
            SELECT keyword AS concept, last_seen_ts AS timestamp, predicted_recall AS memory_score
            FROM memory_decay
            WHERE keyword = ?
            ORDER BY last_seen_ts ASC
        """
        df = pd.read_sql(query, conn, params=(concept,))
    else:
        query = """
            SELECT keyword AS concept, last_seen_ts AS timestamp, predicted_recall AS memory_score
            FROM memory_decay
            ORDER BY last_seen_ts ASC
        """
        df = pd.read_sql(query, conn)
    conn.close()
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce', utc=True)
        df["memory_score"] = pd.to_numeric(df["memory_score"], errors='coerce')
        df.dropna(subset=["timestamp", "memory_score"], inplace=True)
    return df

def predicted_forgetting_curve(lambda_val=0.1, hours=24, points=50):
    times = np.linspace(0, hours, points)
    scores = np.exp(-lambda_val * times)
    return times, scores

def fetch_logs():
    conn = sqlite3.connect(DB_PATH)
    df_logs = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    conn.close()
    # Ensure datetime
    for col in ['start_ts', 'end_ts']:
        if col in df_sessions.columns:
            df_sessions[col] = pd.to_datetime(df_sessions[col], errors='coerce', utc=True)
    if 'timestamp' in df_logs.columns:
        df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'], errors='coerce', utc=True)
    return df_logs, df_sessions

# -----------------------------
# Tabs Layout
# -----------------------------
tabs = st.tabs(["Overview", "Knowledge Graph", "Memory Decay", "OCR & App Usage"])

# -----------------------------
# TAB 1: Overview / Quick Stats
# -----------------------------
with tabs[0]:
    st.title("🔮 Forgotten Knowledge Tracker - Overview")

    # Quick Stats
    df_logs, df_sessions = fetch_logs()
    total_minutes = 0
    total_keywords = 0
    focus_level = "N/A"
    if not df_logs.empty:
        df_logs['ocr_keywords'] = df_logs['ocr_keywords'].apply(lambda x: eval(x) if x else [])
        total_keywords = sum(len(k) for k in df_logs['ocr_keywords'])
        focus_level = df_logs['intent_label'].iloc[-1] if 'intent_label' in df_logs.columns else "N/A"
    if not df_sessions.empty:
        total_minutes = ((df_sessions['end_ts'] - df_sessions['start_ts']).dt.total_seconds()/60).sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("App Usage (hrs)", f"{total_minutes/60:.1f}")
    col2.metric("Total OCR Keywords", total_keywords)
    col3.metric("Latest Audio Label", df_logs['audio_label'].iloc[-1] if 'audio_label' in df_logs.columns and not df_logs.empty else "N/A")
    col4.metric("Focus Level", focus_level)

# -----------------------------
# TAB 2: Knowledge Graph
# -----------------------------
with tabs[1]:
    st.subheader("📚 Knowledge Graph Concepts")
    if len(G.nodes) == 0:
        st.warning("Knowledge graph is empty. Run the tracker first!")
    else:
        table_data = []
        for node in G.nodes:
            mem_score = G.nodes[node].get('memory_score', 0.3)
            next_review = G.nodes[node].get('next_review_time', "N/A")
            table_data.append({"Concept": node, "Memory Score": round(mem_score, 2), "Next Review": next_review})
        df = pd.DataFrame(table_data)
        st.dataframe(df.style.bar(subset=['Memory Score'], color='#7c4dff'), use_container_width=True)

        # Graph Visualization
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
# TAB 3: Memory Decay
# -----------------------------
with tabs[2]:
    st.subheader("📉 Memory Decay Curves")
    df_decay = fetch_memory_decay()
    if df_decay.empty:
        st.warning("No memory decay data found yet. Run the tracker to generate data.")
    else:
        fig = px.line(df_decay, x="timestamp", y="memory_score", color="concept",
                      markers=True, title="Forgetting Curve / Memory Decay per Concept",
                      labels={"timestamp": "Time", "memory_score": "Predicted Recall"})
        fig.update_layout(legend_title_text="Concept", yaxis=dict(range=[0, 1]))
        st.plotly_chart(fig, use_container_width=True)

    # Individual Concept Selector
    st.subheader("🧠 Individual Concept Decay Viewer")
    concepts = list(G.nodes)
    selected_concepts = st.multiselect("Select concepts", concepts, default=concepts[:3])
    if selected_concepts:
        fig_decay_ind = go.Figure()
        for concept in selected_concepts:
            df_concept = fetch_memory_decay(concept)
            if not df_concept.empty:
                fig_decay_ind.add_trace(go.Scatter(
                    x=df_concept['timestamp'],
                    y=df_concept['memory_score'],
                    mode='lines+markers',
                    name=concept
                ))
        fig_decay_ind.update_layout(title="Memory Decay Over Time (Selected Concepts)",
                                    xaxis_title="Time", yaxis_title="Memory Score", yaxis=dict(range=[0, 1]))
        st.plotly_chart(fig_decay_ind, use_container_width=True)

    # Predicted forgetting overlay
    st.subheader("📈 Predicted Forgetting Curve Overlay")
    if concepts:
        concept_pred = st.selectbox("Choose concept for prediction", concepts)
        times, scores = predicted_forgetting_curve()
        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=[datetime.now() + timedelta(hours=t) for t in times],
            y=scores,
            mode='lines',
            name=f"Predicted {concept_pred}"
        ))
        fig_pred.update_layout(title=f"Predicted Forgetting Curve for {concept_pred}",
                               xaxis_title="Time", yaxis_title="Predicted Recall", yaxis=dict(range=[0, 1]))
        st.plotly_chart(fig_pred, use_container_width=True)

# -----------------------------
# TAB 4: OCR & App Usage
# -----------------------------
with tabs[3]:
    st.subheader("📝 OCR Keyword Analytics & App Usage")

    if not df_logs.empty:
        # OCR Keywords
        df_keywords = []
        for row in df_logs.itertuples():
            kws = row.ocr_keywords if hasattr(row, 'ocr_keywords') else []
            timestamp = row.timestamp if hasattr(row, 'timestamp') else pd.Timestamp.now()
            for k in kws:
                df_keywords.append({"Keyword": k, "Timestamp": timestamp})
        if df_keywords:
            df_kw = pd.DataFrame(df_keywords)
            # Top keywords
            top_kw = df_kw['Keyword'].value_counts().head(10)
            st.markdown("**Top 10 OCR Keywords:**")
            st.bar_chart(top_kw)

            # Keyword trend over time
            kw_trend = df_kw.groupby([pd.Grouper(key='Timestamp', freq='D'), 'Keyword']).size().reset_index(name='Count')
            fig_kw_trend = px.line(kw_trend, x='Timestamp', y='Count', color='Keyword', title="Keyword Trends Over Time")
            st.plotly_chart(fig_kw_trend, use_container_width=True)
    else:
        st.warning("No OCR logs found.")

    # App Usage Heatmap
    if not df_sessions.empty:
        df_sessions['Duration'] = (df_sessions['end_ts'] - df_sessions['start_ts']).dt.total_seconds()/60
        heatmap_df = df_sessions.groupby(['app_name', df_sessions['start_ts'].dt.date])['Duration'].sum().reset_index()
        heatmap_pivot = heatmap_df.pivot(index='app_name', columns='start_ts', values='Duration').fillna(0)

        fig_heat = go.Figure(
            data=go.Heatmap(
                z=heatmap_pivot.values,
                x=[str(d) for d in heatmap_pivot.columns],
                y=heatmap_pivot.index,
                colorscale="Viridis",
                hovertemplate="App: %{y}<br>Date: %{x}<br>Duration: %{z:.1f} mins<extra></extra>"
            )
        )
        fig_heat.update_layout(title="App Usage Duration Heatmap", xaxis_title="Date", yaxis_title="App")
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.warning("No session logs found for heatmap.")
