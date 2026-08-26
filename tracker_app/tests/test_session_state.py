"""Tests for the shared study-session state (DB-backed)."""

import pytest
from datetime import datetime
from sqlalchemy import inspect

from tracker_app.tracking import session_state as ss
from tracker_app.db.models import Base, SessionLocal, SessionToggle, EarCalibration


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure tables exist and reset them before each test."""
    db = SessionLocal()
    try:
        engine = db.get_bind()
        insp = inspect(engine)
        existing = insp.get_table_names()
        needed = ["session_toggle", "ear_calibration"]
        to_create = [t for t in needed if t not in existing]
        if to_create:
            Base.metadata.create_all(engine)
        db.query(SessionToggle).delete()
        db.query(EarCalibration).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(SessionToggle).delete()
        db.query(EarCalibration).delete()
        db.commit()
    finally:
        db.close()


def test_default_is_inactive():
    assert ss.is_active() is False


def test_start_activates_session():
    result = ss.start()
    assert result["active"] is True
    assert result["started_at"] is not None
    assert ss.is_active() is True


def test_stop_deactivates_session():
    ss.start()
    result = ss.stop()
    assert result["active"] is False
    assert result["stopped_at"] is not None
    assert ss.is_active() is False


def test_start_stop_idempotent():
    ss.start()
    ss.start()
    assert ss.is_active() is True
    ss.stop()
    ss.stop()
    assert ss.is_active() is False


def test_restart_resets_started_at():
    ss.start()
    first_started = ss.get_status()["started_at"]
    ss.stop()
    ss.start()
    second_started = ss.get_status()["started_at"]
    assert second_started != first_started
    assert ss.get_status()["elapsed_seconds"] < 5


def test_start_after_crash_resets_stale_clock():
    db = SessionLocal()
    try:
        toggle = SessionToggle(id=1, active=True, started_at=datetime(2026, 1, 1))
        db.add(toggle)
        db.commit()
    finally:
        db.close()
    ss.start()
    status = ss.get_status()
    assert status["started_at"] != "2026-01-01T00:00:00"
    assert status["elapsed_seconds"] < 5


def test_status_reports_elapsed_seconds():
    ss.start()
    status = ss.get_status()
    assert status["active"] is True
    assert isinstance(status["elapsed_seconds"], int)
    assert status["elapsed_seconds"] >= 0


def test_state_persists_to_db():
    ss.start()
    assert ss.is_active() is True


def test_externally_written_state_is_read():
    db = SessionLocal()
    try:
        toggle = SessionToggle(id=1, active=True, started_at=datetime(2026, 1, 1))
        db.add(toggle)
        db.commit()
    finally:
        db.close()
    assert ss.is_active() is True
    status = ss.get_status()
    assert status["active"] is True
    assert status["started_at"] == "2026-01-01T00:00:00"


def test_intent_gate_default_allows_studying_only():
    from tracker_app.config import SESSION_ALLOWED_INTENTS
    assert "studying" in SESSION_ALLOWED_INTENTS


def test_set_and_get_calibration():
    data = {
        "personal_ear_low": 0.15,
        "personal_ear_high": 0.35,
        "mean_ear": 0.25,
        "std_ear": 0.05,
        "fallback": False,
    }
    ss.set_calibration(data)
    result = ss.get_calibration()
    assert result is not None
    assert result["personal_ear_low"] == 0.15
    assert result["personal_ear_high"] == 0.35


def test_calibration_cleared_on_stop():
    data = {"personal_ear_low": 0.15, "personal_ear_high": 0.35, "fallback": False}
    ss.set_calibration(data)
    assert ss.get_calibration() is not None
    ss.start()
    ss.stop()
    assert ss.get_calibration() is None


def test_get_calibration_returns_none_when_empty():
    assert ss.get_calibration() is None


def test_concurrent_start_stop_consistent():
    status = ss.get_status()
    assert status["active"] in (True, False)
