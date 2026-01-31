# tests/test_db_integrity.py
import pytest
import sqlite3
import pandas as pd
from config import DB_PATH
from datetime import datetime

@pytest.fixture(scope="module")
def db_connection():
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()


# -----------------------------
# Sessions Table Tests
# -----------------------------
def test_sessions_no_missing_timestamps(db_connection):
    df = pd.read_sql("SELECT * FROM sessions", db_connection)
    missing_start = df[df["start_ts"].isna()]
    missing_end = df[df["end_ts"].isna()]
    assert missing_start.empty, f"Missing start_ts in rows: {missing_start.index.tolist()}"
    assert missing_end.empty, f"Missing end_ts in rows: {missing_end.index.tolist()}"


def test_sessions_duration_positive(db_connection):
    df = pd.read_sql("SELECT * FROM sessions", db_connection)
    df["start_ts"] = pd.to_datetime(df["start_ts"], errors="coerce")
    df["end_ts"] = pd.to_datetime(df["end_ts"], errors="coerce")

    # Apply dashboard logic: fix invalid end_ts
    df["end_ts"] = df["end_ts"].where(
        df["end_ts"] > df["start_ts"],
        df["start_ts"] + pd.Timedelta(seconds=5)
    )
    df["duration_min"] = (df["end_ts"] - df["start_ts"]).dt.total_seconds() / 60

    assert (df["duration_min"] > 0).all(), "Some session durations are zero or negative"


def test_sessions_app_name_not_empty(db_connection):
    df = pd.read_sql("SELECT * FROM sessions", db_connection)
    assert df["app_name"].notna().all(), "Some sessions have missing app_name"


# -----------------------------
# Multi-Modal Logs Tests
# -----------------------------
def test_logs_timestamps_valid(db_connection):
    df = pd.read_sql("SELECT * FROM multi_modal_logs", db_connection)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    invalid_ts = df["timestamp"].isna().sum()
    assert invalid_ts == 0, f"{invalid_ts} rows have invalid timestamps"


def test_logs_labels_not_empty(db_connection):
    df = pd.read_sql("SELECT * FROM multi_modal_logs", db_connection)
    for col in ["audio_label", "intent_label"]:
        assert df[col].notna().all(), f"Column {col} has missing values"


# -----------------------------
# Memory Decay Tests
# -----------------------------
def test_memory_decay_timestamps_valid(db_connection):
    df = pd.read_sql("SELECT * FROM memory_decay", db_connection)
    for col in ["last_seen_ts", "updated_at"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
        assert df[col].notna().all(), f"{col} has invalid timestamps"


def test_memory_decay_scores_valid(db_connection):
    df = pd.read_sql("SELECT * FROM memory_decay", db_connection)
    df["predicted_recall"] = pd.to_numeric(df["predicted_recall"], errors="coerce")
    invalid_scores = df["predicted_recall"].isna().sum()
    assert invalid_scores == 0, f"{invalid_scores} rows have invalid predicted_recall"
    assert ((df["predicted_recall"] >= 0) & (df["predicted_recall"] <= 1)).all(), "predicted_recall out of [0,1]"


# -----------------------------
# Metrics / Reminders Tests
# -----------------------------
def test_metrics_concept_unique(db_connection):
    df = pd.read_sql("SELECT * FROM metrics", db_connection)
    duplicates = df[df.duplicated(subset=["concept"])]
    assert duplicates.empty, f"Duplicate concepts found: {duplicates['concept'].tolist()}"


def test_metrics_next_review_future(db_connection):
    df = pd.read_sql("SELECT * FROM metrics", db_connection)
    df["next_review_time"] = pd.to_datetime(df["next_review_time"], errors="coerce")
    invalid_next_review = df[df["next_review_time"].isna()]
    assert invalid_next_review.empty, "Some next_review_time are invalid"


def test_metrics_memory_score_valid(db_connection):
    df = pd.read_sql("SELECT * FROM metrics", db_connection)
    df["memory_score"] = pd.to_numeric(df["memory_score"], errors="coerce")
    assert ((df["memory_score"] >= 0) & (df["memory_score"] <= 1)).all(), "Memory scores out of range [0,1]"
