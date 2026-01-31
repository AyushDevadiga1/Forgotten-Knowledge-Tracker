# tests/test_data_analysis.py
import pytest
import pandas as pd
from dashboard.dashboard import load_cleaned_data

@pytest.fixture(scope="module")
def data():
    """Load cleaned data for tests."""
    return load_cleaned_data()

def test_sessions_no_missing_timestamps(data):
    df_sessions, _, _, _ = data
    # Check for missing timestamps
    assert df_sessions["start_ts"].notna().all(), "Some start_ts are missing"
    assert df_sessions["end_ts"].notna().all(), "Some end_ts are missing"

def test_sessions_duration_positive(data):
    df_sessions, _, _, _ = data
    df_sessions["duration_min"] = (df_sessions["end_ts"] - df_sessions["start_ts"]).dt.total_seconds() / 60
    # Durations should be >= 0
    assert (df_sessions["duration_min"] >= 0).all(), "Some session durations are negative"

def test_sessions_valid_app_names(data):
    df_sessions, _, _, _ = data
    # Check that app_name is not empty
    assert df_sessions["app_name"].notna().all(), "Some app_name entries are missing"

def test_memory_scores_in_range(data):
    _, _, df_decay, df_metrics = data
    # Memory scores must be between 0 and 1
    if not df_decay.empty:
        df_decay["memory_score"] = pd.to_numeric(df_decay["memory_score"], errors='coerce')
        assert ((df_decay["memory_score"] >= 0) & (df_decay["memory_score"] <= 1)).all(), "Memory decay scores out of range"
    if not df_metrics.empty:
        df_metrics["memory_score"] = pd.to_numeric(df_metrics["memory_score"], errors='coerce')
        assert ((df_metrics["memory_score"] >= 0) & (df_metrics["memory_score"] <= 1)).all(), "Metrics memory scores out of range"

def test_multi_modal_logs_valid(data):
    _, df_logs, _, _ = data
    # Check required columns exist
    required_cols = ["timestamp", "attention_score", "audio_label", "window_title"]
    for col in required_cols:
        assert col in df_logs.columns, f"{col} is missing from multi_modal_logs"
    # Check timestamps
    assert df_logs["timestamp"].notna().all(), "Some log timestamps are missing"

def test_upcoming_reminders_future(data):
    _, _, _, df_metrics = data
    # Next review times should be in the future
    now = pd.Timestamp.now()
    future_reviews = df_metrics["next_review_time"] > now
    # Allow empty metrics table
    if not df_metrics.empty:
        assert future_reviews.any(), "No upcoming reminders found"
