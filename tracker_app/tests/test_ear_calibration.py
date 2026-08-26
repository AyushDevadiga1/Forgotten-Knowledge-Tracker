"""Tests for EAR per-user calibration (F-5)."""

import pytest
import numpy as np


@pytest.fixture
def isolated_state():
    from tracker_app.db.models import Base, SessionLocal, SessionToggle, EarCalibration
    from sqlalchemy import inspect

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


@pytest.fixture
def mock_webcam(monkeypatch):
    from tracker_app.tracking import webcam_module as wm

    class FakeLandmark:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    def make_face_landmarks():
        """Return an object with a .landmark list of 400 FakeLandmarks."""
        obj = type("FL", (), {})()
        obj.landmark = [FakeLandmark(0.3, 0.3) for _ in range(400)]
        return obj

    class FakeResults:
        multi_face_landmarks = [make_face_landmarks()]

    class FakeFaceMesh:
        def process(self, rgb_frame):
            return FakeResults()

    monkeypatch.setattr(wm, "capture_frame", lambda: np.zeros((480, 640, 3), dtype=np.uint8))
    monkeypatch.setattr(wm, "_get_face_mesh", lambda: FakeFaceMesh())
    return wm


def test_calibrate_ear_returns_valid_dict(mock_webcam, monkeypatch):
    from tracker_app.tracking.webcam_module import calibrate_ear
    from tracker_app.tracking import webcam_module as wm

    # Mock eye_aspect_ratio to return a fixed value
    # Return varying EAR values to simulate real eye movement
    import itertools

    ear_cycle = itertools.cycle([0.22, 0.25, 0.28, 0.30, 0.27])
    monkeypatch.setattr(wm, "eye_aspect_ratio", lambda lm, idx: next(ear_cycle))

    # Patch min samples so 1s of capture is enough
    monkeypatch.setattr("tracker_app.config.CALIBRATION_MIN_SAMPLES", 5)
    result = calibrate_ear(duration_seconds=2)
    assert "personal_ear_low" in result
    assert "personal_ear_high" in result
    assert "mean_ear" in result
    assert "std_ear" in result
    assert "fallback" in result
    assert result["fallback"] is False
    assert result["personal_ear_low"] < result["mean_ear"] < result["personal_ear_high"]


def test_calibrate_ear_fallback_on_no_face(monkeypatch):
    from tracker_app.tracking.webcam_module import calibrate_ear
    from tracker_app.tracking import webcam_module as wm

    # Mock capture_frame to always return None (no camera)
    monkeypatch.setattr(wm, "capture_frame", lambda: None)

    # Patch min samples so 1s of capture is enough
    monkeypatch.setattr("tracker_app.config.CALIBRATION_MIN_SAMPLES", 5)
    result = calibrate_ear(duration_seconds=2)
    assert result["fallback"] is True


def test_compute_attention_score_with_calibration():
    from tracker_app.tracking.webcam_module import compute_attention_score

    ear_values = [0.25, 0.26, 0.27, 0.28, 0.29]
    # With calibration: low=0.20, high=0.35 (same as defaults)
    score_default = compute_attention_score(ear_values)
    score_calibrated = compute_attention_score(ear_values, ear_low=0.20, ear_high=0.35)
    assert score_default == score_calibrated

    # With personal thresholds (tighter range)
    score_personal = compute_attention_score(ear_values, ear_low=0.22, ear_high=0.30)
    assert 0 <= score_personal <= 100


def test_compute_attention_score_fallback_to_defaults():
    from tracker_app.tracking.webcam_module import compute_attention_score

    ear_values = [0.25]
    # No calibration args = default 0.2/0.35
    score = compute_attention_score(ear_values)
    assert 40 <= score <= 100


def test_session_state_calibration_round_trip(isolated_state):
    from tracker_app.tracking import session_state as ss

    cal_data = {
        "personal_ear_low": 0.15,
        "personal_ear_high": 0.30,
        "mean_ear": 0.23,
        "std_ear": 0.05,
        "fallback": False,
        "calibrated_at": "2026-01-01T00:00:00",
    }
    ss.set_calibration(cal_data)
    result = ss.get_calibration()
    assert result == cal_data


def test_stop_clears_calibration(isolated_state):
    from tracker_app.tracking import session_state as ss

    ss.start()
    ss.set_calibration(
        {
            "personal_ear_low": 0.15,
            "personal_ear_high": 0.30,
            "fallback": False,
        }
    )
    assert ss.get_calibration() is not None
    ss.stop()
    # After stop, calibration should be cleared
    status = ss.get_status()
    assert status.get("ear_calibration") is None


def test_get_status_includes_calibration(isolated_state):
    from tracker_app.tracking import session_state as ss

    ss.start()
    cal = {
        "personal_ear_low": 0.18,
        "personal_ear_high": 0.32,
        "fallback": False,
    }
    ss.set_calibration(cal)
    status = ss.get_status()
    assert status["ear_calibration"] == cal


def test_get_calibration_returns_none_when_empty(isolated_state):
    from tracker_app.tracking import session_state as ss

    assert ss.get_calibration() is None
