"""Runtime telemetry writers (P5/D5): the tracker session path itself writes
multi_modal_logs and metrics rows, and the telemetry summary counts them
within its 24-hour window (task 5.4).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import tracker_app.learning.concept_scheduler as cs_mod
from tracker_app.db import models
from tracker_app.db.models import Base, Metric, MultiModalLog, TrackingSession
from tracker_app.tracking import activity_monitor as am
from tracker_app.tracking.activity_monitor import ActivityMonitor


@pytest.fixture
def db_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "SessionLocal", TestSession)
    monkeypatch.setattr(am, "SessionLocal", TestSession)
    monkeypatch.setattr(cs_mod, "SessionLocal", TestSession)
    return TestSession


@pytest.fixture
def monitor(db_session):
    return ActivityMonitor()


def test_session_path_writes_log_and_metric_rows(db_session, monitor):
    monitor.start_session()
    monitor.process_concepts(
        {
            "neural network": {"score": 0.8, "count": 2},
            "backpropagation": {"score": 0.7, "count": 1},
        },
        attention_score=60.5,
        context_text="neural network training and backpropagation step",
    )
    monitor.log_multimodal(
        window_title="notepad",
        keywords={"neural network": {"score": 0.8}},
        audio_label="speech",
        attention_score=60.5,
        interaction_rate=3.0,
        intent_label="studying",
        intent_confidence=0.9,
    )
    monitor.end_session()

    with db_session() as db:
        logs = db.query(MultiModalLog).all()
        assert len(logs) == 1
        assert logs[0].window_title == "notepad"
        assert logs[0].intent_label == "studying"

        metrics = db.query(Metric).all()
        assert len(metrics) == 2
        assert {m.concept for m in metrics} == {"neural network", "backpropagation"}
        assert all(m.memory_score is not None for m in metrics)

        sessions = db.query(TrackingSession).all()
        assert len(sessions) == 1


def test_telemetry_summary_counts_runtime_rows(db_session, monitor):
    from tracker_app.web.app import app

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    client = app.test_client()

    monitor.start_session()
    monitor.process_concepts(
        {"neural network": {"score": 0.8, "count": 2}},
        attention_score=60.0,
        context_text="neural network cross entropy loss",
    )
    monitor.log_multimodal(
        window_title="chrome",
        keywords={"neural network": {"score": 0.8}},
        audio_label="silence",
        attention_score=60.0,
        interaction_rate=2.0,
        intent_label="studying",
        intent_confidence=0.9,
    )
    monitor.end_session()

    resp = client.get("/api/v1/telemetry/summary")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["total_logs"] == 1
    assert data["top_keywords"][0]["keyword"] == "neural network"
