# dashboard.py - ENHANCED VERSION
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from config import ENHANCED_DB_PATH, DB_PATH
import numpy as np

def init_session_state():
    """Initialize session state variables"""
    if 'db_choice' not in st.session_state:
        st.session_state.db_choice = "Enhanced Database"
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()

def get_db_connection(db_choice):
    """Get database connection based on choice"""
    if db_choice == "Enhanced Database":
        return sqlite3.connect(ENHANCED_DB_PATH)
    else:
        return sqlite3.connect(DB_PATH)

def get_enhanced_stats(conn):
    """Get statistics from enhanced database"""
    stats = {}
    
    # Session statistics
    df_sessions = pd.read_sql_query("""
        SELECT COUNT(*) as total_sessions,
               AVG(attention_score) as avg_attention,
               AVG(interaction_rate) as avg_interaction,
               AVG(intent_confidence) as avg_intent_confidence
        FROM enhanced_sessions 
        WHERE timestamp > datetime('now', '-7 days')
    """, conn)
    
    if not df_sessions.empty:
        stats['total_sessions'] = df_sessions.iloc[0]['total_sessions']
        stats['avg_attention'] = df_sessions.iloc[0]['avg_attention'] or 0
        stats['avg_interaction'] = df_sessions.iloc[0]['avg_interaction'] or 0
        stats['avg_intent_confidence'] = df_sessions.iloc[0]['avg_intent_confidence'] or 0
    
    # Concept statistics
    df_concepts = pd.read_sql_query("""
        SELECT COUNT(*) as total_concepts,
               AVG(memory_score) as avg_memory_score
        FROM concept_memory_predictions 
        WHERE timestamp > datetime('now', '-7 days')
    """, conn)
    
    if not df_concepts.empty:
        stats['total_concepts'] = df_concepts.iloc[0]['total_concepts']
        stats['avg_memory_score'] = df_concepts.iloc[0]['avg_memory_score'] or 0
    
    return stats

def create_attention_trend_chart(conn):
    """Create attention trend chart"""
    df = pd.read_sql_query("""
        SELECT date(timestamp) as date, 
               AVG(attention_score) as avg_attention,
               AVG(interaction_rate) as avg_interaction
        FROM enhanced_sessions 
        WHERE timestamp > datetime('now', '-7 days')
        GROUP BY date(timestamp)
        ORDER BY date
    """, conn)
    
    if df.empty:
        return None
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['avg_attention'], 
                            name='Attention Score', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df['date'], y=df['avg_interaction'], 
                            name='Interaction Rate', line=dict(color='green')))
    
    fig.update_layout(
        title='Attention and Interaction Trends (7 Days)',
        xaxis_title='Date',
        yaxis_title='Score',
        hovermode='x unified'
    )
    
    return fig

def create_intent_distribution_chart(conn):
    """Create intent distribution chart"""
    df = pd.read_sql_query("""
        SELECT intent_label, COUNT(*) as count
        FROM enhanced_sessions 
        WHERE intent_label IS NOT NULL 
        AND timestamp > datetime('now', '-7 days')
        GROUP BY intent_label
    """, conn)
    
    if df.empty:
        return None
    
    fig = px.pie(df, values='count', names='intent_label', 
                 title='User Intent Distribution')
    return fig

def create_memory_score_chart(conn):
    """Create memory score distribution chart"""
    df = pd.read_sql_query("""
        SELECT memory_score, COUNT(*) as count
        FROM concept_memory_predictions 
        WHERE timestamp > datetime('now', '-7 days')
        GROUP BY memory_score
        ORDER BY memory_score
    """, conn)
    
    if df.empty:
        return None
    
    fig = px.histogram(df, x='memory_score', y='count', 
                       title='Memory Score Distribution',
                       nbins=20)
    fig.update_layout(xaxis_title='Memory Score', yaxis_title='Count')
    return fig

def show_enhanced_dashboard(conn):
    """Show enhanced dashboard with charts and analytics"""
    
    # Statistics cards
    stats = get_enhanced_stats(conn)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Sessions", stats.get('total_sessions', 0))
    with col2:
        st.metric("Avg Attention", f"{stats.get('avg_attention', 0):.1f}")
    with col3:
        st.metric("Avg Interaction", f"{stats.get('avg_interaction', 0):.1f}")
    with col4:
        st.metric("Avg Memory Score", f"{stats.get('avg_memory_score', 0):.2f}")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        attention_chart = create_attention_trend_chart(conn)
        if attention_chart:
            st.plotly_chart(attention_chart, use_container_width=True)
        else:
            st.info("No attention data available for the last 7 days")
    
    with col2:
        intent_chart = create_intent_distribution_chart(conn)
        if intent_chart:
            st.plotly_chart(intent_chart, use_container_width=True)
        else:
            st.info("No intent data available")
    
    # Memory scores
    memory_chart = create_memory_score_chart(conn)
    if memory_chart:
        st.plotly_chart(memory_chart, use_container_width=True)
    
    # Recent sessions table
    st.subheader("📊 Recent Sessions")
    df_sessions = pd.read_sql_query("""
        SELECT timestamp, window_title, app_type, interaction_rate, 
               attention_score, intent_label, intent_confidence
        FROM enhanced_sessions 
        ORDER BY timestamp DESC 
        LIMIT 50
    """, conn)
    
    if not df_sessions.empty:
        # Format timestamp
        df_sessions['timestamp'] = pd.to_datetime(df_sessions['timestamp'])
        df_sessions['timestamp'] = df_sessions['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(df_sessions, use_container_width=True)
    else:
        st.info("No enhanced sessions data available")

def show_original_dashboard(conn):
    """Show original database dashboard"""
    df_sessions = pd.read_sql_query("""
        SELECT start_ts, app_name, window_title, interaction_rate
        FROM sessions 
        ORDER BY start_ts DESC 
        LIMIT 100
    """, conn)
    
    if not df_sessions.empty:
        st.metric("Total Sessions", len(df_sessions))
        
        # Basic statistics
        col1, col2 = st.columns(2)
        with col1:
            avg_interaction = df_sessions['interaction_rate'].mean()
            st.metric("Avg Interaction Rate", f"{avg_interaction:.1f}")
        
        with col2:
            unique_apps = df_sessions['app_name'].nunique()
            st.metric("Unique Applications", unique_apps)
        
        st.dataframe(df_sessions, use_container_width=True)
    else:
        st.info("No session data available in original database")

def main():
    st.set_page_config(
        page_title="Forgotten Knowledge Tracker",
        page_icon="🔮",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="main-header">🔮 Forgotten Knowledge Tracker Dashboard</div>', 
                unsafe_allow_html=True)
    
    init_session_state()
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        
        db_choice = st.selectbox(
            "Select Database",
            ["Enhanced Database", "Original Database"],
            key='db_choice'
        )
        
        st.info(f"Using: {db_choice}")
        
        if st.button("Refresh Data"):
            st.session_state.last_refresh = datetime.now()
            st.rerun()
        
        st.write(f"Last refresh: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
        
        # Database info
        try:
            conn = get_db_connection(db_choice)
            if db_choice == "Enhanced Database":
                table_info = pd.read_sql_query(
                    "SELECT name FROM sqlite_master WHERE type='table'", conn)
                st.write("Tables:", ", ".join(table_info['name'].tolist()))
            conn.close()
        except:
            pass
    
    # Main content
    try:
        conn = get_db_connection(db_choice)
        
        if db_choice == "Enhanced Database":
            show_enhanced_dashboard(conn)
        else:
            show_original_dashboard(conn)
        
        conn.close()
        
    except Exception as e:
        st.error(f"Database error: {e}")
        st.info("Please make sure the tracker has been run at least once to create the database.")

if __name__ == "__main__":
    main()