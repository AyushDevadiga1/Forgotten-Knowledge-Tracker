"""Focused-tab persistence end-to-end (real SQLite via init_all_databases).

The loop forwards the captured tab into process_intent / log_multimodal and the
web API forwards it into FeedbackTrainingSample. These tests pin that each
persistence boundary actually stores the tab fields - and that no-tab cycles
store NULLs - so retraining (ADR-003) can consume the tab signal.

Run: python -m pytest tracker_app/tests/test_focused_tab_persistence.py -v
"""

import json
import sqlite3

import pytest

import tracker_app.db.models as models
from tracker_app.db.db_module import init_all_databases
from tracker_app.db.migrations import run_migrations
from tracker_app.db.models import FeedbackTrainingSample, IntentPrediction, MultiModalLog
from tracker_app.tracking import activity_monitor
from tracker_app.tracking.activity_monitor import ActivityMonitor
from tracker_app.web.routes.intent import FeedbackService


def _use_db(monkeypatch, db_file):
    """Point the lazy ORM engine/session machinery at a throwaway DB."""
    monkeypatch.setenv("FKT_TEST_DB", db_file)
    monkeypatch.setattr(models, "_engine", None)
    monkeypatch.setattr(models, "_SessionLocal", None)


@pytest.fixture
def db(monkeypatch, tmp_path):
    db_file = str(tmp_path / "tab.db")
    _use_db(monkeypatch, db_file)
    init_all_databases()  # create_all + run_migrations (014 adds the tab columns)
    Session = models.get_session_local()
    monkeypatch.setattr(activity_monitor, "SessionLocal", Session)
    yield Session
    engine = models._engine
    if engine is not None:
        engine.dispose()
    models._engine = None
    models._SessionLocal = None


def _latest_multimodal(Session):
    with Session() as s:
        return s.query(MultiModalLog).order_by(MultiModalLog.id.desc()).first()


def _latest_prediction(Session):
    with Session() as s:
        return s.query(IntentPrediction).order_by(IntentPrediction.id.desc()).first()


def test_log_multimodal_persists_focused_tab_json(db):
    ActivityMonitor().log_multimodal(
        window_title="pytest",
        keywords={},
        intent_label="studying",
        focused_tab={"title": "Two Sum - LeetCode", "url": "https://leetcode.com/problems/two-sum/"},
    )
    row = _latest_multimodal(db)
    assert row is not None
    assert json.loads(row.focused_tab) == {
        "title": "Two Sum - LeetCode",
        "url": "https://leetcode.com/problems/two-sum/",
    }


def test_log_multimodal_no_tab_leaves_focused_tab_null(db):
    ActivityMonitor().log_multimodal(window_title="pytest", keywords={})
    assert _latest_multimodal(db).focused_tab is None


def test_process_intent_persists_tab_to_prediction(db):
    monitor = ActivityMonitor()
    monitor.process_intent(
        {"intent_label": "studying", "confidence": 0.9, "features": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]},
        context="LeetCode - Two Sum",
        focused_tab_title="Two Sum - LeetCode",
        focused_tab_url="https://leetcode.com/problems/two-sum/",
    )
    row = _latest_prediction(db)
    assert row.focused_tab_title == "Two Sum - LeetCode"
    assert row.focused_tab_url == "https://leetcode.com/problems/two-sum/"


def test_feedback_sample_forwards_tab_fields(db):
    monitor = ActivityMonitor()
    monitor.process_intent(
        {"intent_label": "studying", "confidence": 0.9, "features": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]},
        context="LeetCode - Two Sum",
        focused_tab_title="Two Sum - LeetCode",
        focused_tab_url="https://leetcode.com/problems/two-sum/",
    )
    pred = _latest_prediction(db)

    FeedbackService.record_feedback(pred.id, is_correct=False, actual_intent="passive")

    with db() as s:
        sample = s.query(FeedbackTrainingSample).order_by(FeedbackTrainingSample.id.desc()).first()
        assert sample is not None
        assert sample.focused_tab_title == "Two Sum - LeetCode"
        assert sample.focused_tab_url == "https://leetcode.com/problems/two-sum/"


def test_migration_014_adds_tab_columns_to_stale_tables(tmp_path):
    conn = sqlite3.connect(db_file := str(tmp_path / "stale_tab.db"))
    try:
        conn.execute("CREATE TABLE feedback_training_samples (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, feature_vector TEXT NOT NULL, predicted_label TEXT NOT NULL, actual_label TEXT NOT NULL, confidence REAL DEFAULT 0.0, window_title TEXT DEFAULT '', used_in_training INTEGER DEFAULT 0)")
        conn.execute("CREATE TABLE intent_predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, intent_label TEXT NOT NULL, confidence REAL, features TEXT, context TEXT)")
        conn.execute("CREATE TABLE multi_modal_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, window_title TEXT, keywords TEXT, intent_label TEXT, audio_label TEXT, attention_score REAL, interaction_rate REAL)")
        conn.commit()
    finally:
        conn.close()

    result = run_migrations(db_path=db_file)
    assert result["failed"] == 0, result["errors"]

    conn = sqlite3.connect(db_file)
    try:
        cols_mm = [r[1] for r in conn.execute("PRAGMA table_info(multi_modal_logs)")]
        cols_fb = [r[1] for r in conn.execute("PRAGMA table_info(feedback_training_samples)")]
        cols_ip = [r[1] for r in conn.execute("PRAGMA table_info(intent_predictions)")]
        assert "focused_tab" in cols_mm
        assert "focused_tab_title" in cols_fb and "focused_tab_url" in cols_fb
        assert "focused_tab_title" in cols_ip and "focused_tab_url" in cols_ip
        migrated = [r[0] for r in conn.execute(
            "SELECT id FROM schema_migrations WHERE id = '014_focused_tab'")]
        assert migrated == ["014_focused_tab"]
        conn.execute(
            "INSERT INTO multi_modal_logs (timestamp, window_title, intent_label)"
            " VALUES ('2026-01-01 00:00:00', 't', 'idle')"
        )
        assert conn.execute("SELECT focused_tab FROM multi_modal_logs").fetchone()[0] is None
    finally:
        conn.close()
