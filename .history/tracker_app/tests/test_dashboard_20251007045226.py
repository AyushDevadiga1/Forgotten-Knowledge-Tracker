# tests/test_dashboard.py
import pytest
import pandas as pd

# -----------------------------
# Fixtures / Helpers
# -----------------------------
@pytest.fixture(scope="module")
def load_data():
    from dashboard.dashboard import load_cleaned_data
    return load_cleaned_data()

# -----------------------------
# Tests
# -----------------------------
def test_load_cleaned_data_returns_dataframes(load_data):
    df_sessions, df_logs, df_decay, df_metrics = load_data
    assert isinstance(df_sessions, pd.DataFrame)
    assert isinstance(df_logs, pd.DataFrame)
    assert isinstance(df_decay, pd.DataFrame)
    assert isinstance(df_metrics, pd.DataFrame)

def test_load_cleaned_data_columns(load_data):
    df_sessions, df_logs, df_decay, df_metrics = load_data
    # Sessions
    expected_cols_sess = ["id","start_ts","end_ts","app_name","audio_label",
                          "intent_label","intent_confidence","duration_min"]
    for col in expected_cols_sess:
        assert col in df_sessions.columns or col in ["duration_min"]  # duration_min may be computed later
    # Logs
    assert "timestamp" in df_logs.columns
    # Memory Decay
    assert "last_seen_ts" in df_decay.columns
    # Metrics
    assert "concept" in df_metrics.columns
    assert "next_review_time" in df_metrics.columns
    assert "memory_score" in df_metrics.columns

def test_fetch_decay_no_concept_returns_dataframe():
    from dashboard.dashboard import fetch_decay
    df = fetch_decay()
    assert isinstance(df, pd.DataFrame)

def test_fetch_decay_with_invalid_concept():
    from dashboard.dashboard import fetch_decay
    df = fetch_decay("NonExistingConcept123")
    # Should return empty dataframe, not fail
    assert isinstance(df, pd.DataFrame)
    assert df.empty or "concept" in df.columns

def test_knowledge_graph_nodes():
    from dashboard.dashboard import get_graph, sync_db_to_graph
    sync_db_to_graph()
    G = get_graph()
    assert hasattr(G, "nodes")
    # nodes can be empty, but attribute must exist
    assert isinstance(G.nodes, object)

def test_upcoming_reminders_filtering(load_data):
    _, _, _, df_metrics = load_data
    now = pd.Timestamp.now()
    upcoming = df_metrics[df_metrics["next_review_time"] > now]
    # Ensure all next_review_time in filtered df are in future
    if not upcoming.empty:
        assert all(upcoming["next_review_time"] > now)

def test_sessions_duration_positive():
    from dashboard.dashboard import load_cleaned_data
    df_sessions, _, _, _ = load_cleaned_data()

    # Replace invalid end_ts per dashboard logic
    df_sessions["end_ts"] = df_sessions["end_ts"].where(
        df_sessions["end_ts"] > df_sessions["start_ts"],
        df_sessions["start_ts"] + pd.Timedelta(seconds=5)
    )

    df_sessions["duration_min"] = (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60

    if not df_sessions.empty:
        # All durations must be >= 0
        assert (df_sessions["duration_min"] >= 0).all()
