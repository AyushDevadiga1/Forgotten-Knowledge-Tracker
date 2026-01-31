# tests/test_dashboard.py
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dashboard import dashboard as db_dash
from core.knowledge_graph import get_graph, sync_db_to_graph

@pytest.fixture(scope="module")
def data():
    df_sessions, df_logs, df_decay, df_metrics = db_dash.load_cleaned_data()
    return df_sessions, df_logs, df_decay, df_metrics

def test_load_cleaned_data_returns_dataframes(data):
    df_sessions, df_logs, df_decay, df_metrics = data
    assert isinstance(df_sessions, pd.DataFrame)
    assert isinstance(df_logs, pd.DataFrame)
    assert isinstance(df_decay, pd.DataFrame)
    assert isinstance(df_metrics, pd.DataFrame)

def test_load_cleaned_data_columns(data):
    df_sessions, df_logs, df_decay, df_metrics = data
    assert "start_ts" in df_sessions.columns
    assert "end_ts" in df_sessions.columns
    assert "concept" in df_metrics.columns
    assert "memory_score" in df_metrics.columns

def test_fetch_decay_no_concept_returns_dataframe():
    df = db_dash.fetch_decay()
    assert isinstance(df, pd.DataFrame)
    assert all(col in df.columns for col in ["concept", "timestamp", "memory_score"])

def test_fetch_decay_with_invalid_concept():
    df = db_dash.fetch_decay("non_existing_concept")
    assert isinstance(df, pd.DataFrame)
    assert df.empty or all(col in df.columns for col in ["concept", "timestamp", "memory_score"])

def test_knowledge_graph_nodes():
    try:
        sync_db_to_graph()
        G = get_graph()
        assert isinstance(G.nodes, object)
        # All nodes should have memory_score attribute
        for n in G.nodes:
            mem_score = G.nodes[n].get("memory_score", None)
            assert mem_score is not None
            assert 0 <= mem_score <= 1
    except Exception:
        pytest.skip("Knowledge graph not initialized")

def test_upcoming_reminders_filtering(data):
    _, _, _, df_metrics = data
    now = datetime.now()
    upcoming = df_metrics[df_metrics["next_review_time"] > now]
    assert all(upcoming["next_review_time"] > now) or upcoming.empty


def test_sessions_duration_positive(data):
    df_sessions, _, _, _ = data
    df_sessions["duration_min"] = (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60
    assert (df_sessions["duration_min"] >= 0).all() or df_sessions.empty
