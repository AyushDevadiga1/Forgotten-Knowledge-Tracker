# test_dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="FKT Test Dashboard", layout="wide")

st.title("🔧 Forgotten Knowledge Tracker - Test Dashboard")

# -----------------------------
# Load Test Data
# -----------------------------
@st.cache_data
def load_test_data():
    sessions = pd.read_csv("test_data/sessions_test.csv")
    logs = pd.read_csv("test_data/logs_test.csv")
    memory_decay = pd.read_csv("test_data/memory_decay_test.csv")

    # Robust timestamp parsing
    for df, cols in [(sessions, ['start_ts','end_ts']),
                     (logs, ['timestamp']),
                     (memory_decay, ['last_seen_ts'])]:
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

    # Ensure memory_score numeric
    if 'memory_score' in memory_decay.columns:
        memory_decay['predicted_recall'] = pd.to_numeric(memory_decay['predicted_recall'], errors='coerce')

    return sessions, logs, memory_decay

sessions, logs, memory_decay = load_test_data()

# -----------------------------
# Quick Overview Cards
# -----------------------------
st.subheader("📊 Quick Stats")

col1, col2, col3, col4 = st.columns(4)

total_minutes = ((sessions['end_ts'] - sessions['start_ts']).dt.total_seconds() / 60).sum()
total_keywords = sum(len(eval(k)) for k in logs['ocr_keywords'])
latest_audio = logs['audio_label'].iloc[-1] if not logs.empty else "N/A"
latest_focus = logs['intent_label'].iloc[-1] if not logs.empty else "N/A"

col1.metric("Total App Usage (hrs)", f"{total_minutes/60:.1f}")
col2.metric("Total Keywords Detected", f"{total_keywords}")
col3.metric("Latest Audio Label", latest_audio)
col4.metric("Latest Focus Level", latest_focus)

# -----------------------------
# Memory Scores Table
# -----------------------------
st.subheader("🧠 Memory Scores Overview")

mem_df = memory_decay.groupby('keyword').agg(
    Memory_Score=('predicted_recall','mean'),
    Last_Seen=('last_seen_ts','max')
).reset_index()

# Designer style: progress bars + table
for idx, row in mem_df.iterrows():
    st.markdown(f"**{row['keyword']}** - Last Seen: {row['Last_Seen']}")
    st.progress(min(max(row['Memory_Score'],0),1))

st.dataframe(mem_df, use_container_width=True)

# -----------------------------
# App Usage Timeline
# -----------------------------
st.subheader("⏱️ Session Timeline")
if not sessions.empty:
    fig_timeline = px.timeline(
        sessions, 
        x_start='start_ts', 
        x_end='end_ts', 
        y='app_name', 
        color='app_name',
        hover_data=['start_ts','end_ts']
    )
    fig_timeline.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_timeline, width='stretch')
else:
    st.warning("No session data available.")

# -----------------------------
# Memory Decay Curves
# -----------------------------
st.subheader("📉 Memory Decay Curves")
if not memory_decay.empty:
    memory_decay['timestamp'] = memory_decay['last_seen_ts']
    fig_decay = px.line(
        memory_decay, x='timestamp', y='predicted_recall', color='keyword',
        markers=True, title="Forgetting Curve / Memory Decay per Concept",
        labels={"timestamp":"Time","predicted_recall":"Memory Score"}
    )
    fig_decay.update_layout(yaxis=dict(range=[0,1]))
    st.plotly_chart(fig_decay, width='stretch')
else:
    st.warning("No memory decay data available.")

# -----------------------------
# Predicted Forgetting Curves
# -----------------------------
st.subheader("📈 Predicted Forgetting Curve Overlay")

def predicted_forgetting_curve(lambda_val=0.1, hours=24, points=50):
    times = np.linspace(0, hours, points)
    scores = np.exp(-lambda_val * times)
    return times, scores

concepts = memory_decay['keyword'].unique()
selected_concept = st.selectbox("Select Concept for Predicted Curve", concepts)

if selected_concept:
    times, scores = predicted_forgetting_curve()
    fig_pred = go.Figure()
    fig_pred.add_trace(go.Scatter(
        x=[datetime.now() + timedelta(hours=t) for t in times],
        y=scores,
        mode='lines',
        name=f"Predicted {selected_concept}"
    ))
    fig_pred.update_layout(
        title=f"Predicted Forgetting Curve for {selected_concept}",
        xaxis_title="Time",
        yaxis_title="Predicted Recall",
        yaxis=dict(range=[0,1])
    )
    st.plotly_chart(fig_pred, width='stretch')

# -----------------------------
# Keyword Trends
# -----------------------------
st.subheader("🔑 Keyword Trends")
if not logs.empty:
    df_trends = []
    for idx, row in logs.iterrows():
        kws = []
        try:
            kws = eval(row['ocr_keywords'])
        except:
            kws = []
        timestamp = row['timestamp']
        for k in kws:
            df_trends.append({"Keyword": k, "Timestamp": timestamp})
    df_trends = pd.DataFrame(df_trends)
    
    if not df_trends.empty:
        fig_kw = px.line(df_trends, x='Timestamp', y='Keyword', title="Keyword Trends Over Time")
        st.plotly_chart(fig_kw, width='stretch')
    else:
        st.warning("No keyword trends to display.")
else:
    st.warning("No OCR logs available.")

