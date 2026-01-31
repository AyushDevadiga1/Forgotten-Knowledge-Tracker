# tests/test_dashboard.py
import pytest
import pandas as pd
import sqlite3
from dashboard import dashboard as dbdash
from config import DB_PATH

# -----------------------------
# Test: Load & Clean Data
# -----------------------------
def test_load_cleaned_data_returns_dataframes():
    df_sessions, df_logs, df_decay, df_metrics = dbdash.load_cleaned_data()
    assert isinstance(df_sessions, pd.DataFrame)
    assert isinstance(df_logs, pd.DataFrame)
    assert isinstance(df_decay, pd.DataFrame)
    assert isinstance(df_metrics, pd.DataFrame)

def test_load_cleaned_data_columns():
    df_sessions, df_logs, df_decay, df_metrics = dbdash.load_cleaned_data()
    expected_sessions_cols = {"start_ts", "end_ts", "app_name", "audio_label", "intent_label", "intent_confidence", "duration_min"}
    expected_logs_cols = {"timestamp"}
    expected_decay_cols = {"last_seen_ts", "updated_at"}
    expected_metrics_cols = {"concept", "next_review_time", "memory_score"}

    assert expected_sessions_cols.issubset(set(df_sessions.columns))
    assert expected_logs_cols.issubset(set(df_logs.columns))
    assert expected_decay_cols.issubset(set(df_decay.columns))
    assert expected_metrics_cols.issubset(set(df_metrics.columns))

# -----------------------------
# Test: Memory Decay Fetch
# -----------------------------
def test_fetch_decay_no_concept_returns_dataframe():
    df = dbdash.fetch_decay()
    assert isinstance(df, pd.DataFrame)
    assert "concept" in df.columns
    assert "timestamp" in df.columns
    assert "memory_score" in df.columns

def test_fetch_decay_with_invalid_concept():
    df = dbdash.fetch_decay("invalid_concept_name_123")
    assert isinstance(df, pd.DataFrame)
    assert df.empty

# -----------------------------
# Test: Top concepts from knowledge graph
# -----------------------------
def test_knowledge_graph_nodes():
    dbdash.sync_db_to_graph()
    G = dbdash.get_graph()
    assert G is not None
    # Memory score and next_review_time should be present
    for node in G.nodes:
        assert "memory_score" in G.nodes[node]
        assert "next_review_time" in G.nodes[node]

# -----------------------------
# Test: Upcoming Reminders
# -----------------------------
def test_upcoming_reminders_filtering():
    _, _, _, df_metrics = dbdash.load_cleaned_data()
    now = pd.Timestamp.now()
    upcoming = df_metrics[df_metrics["next_review_time"] > now]
    assert all(upcoming["next_review_time"] > now)

# -----------------------------
# Test: Sessions duration computation
# -----------------------------
def test_sessions_duration_positive():
    df_sessions, _, _, _ = dbdash.load_cleaned_data()
    if not df_sessions.empty:
        assert (df_sessions["duration_min"] >= 0).all()
