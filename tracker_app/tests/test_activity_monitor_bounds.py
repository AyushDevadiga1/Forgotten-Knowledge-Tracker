"""Tests: ActivityMonitor bounded buffers (M-2/M-3).

M-2: `prediction_buffer` must be a bounded deque (maxlen=100) - it was an
     unbounded list that was never consumed.
M-3: `session_attention_scores` must be a running sum/count (O(1) memory)
     instead of a list that grew forever; the average must be unchanged.

Run: python -m pytest tracker_app/tests/test_activity_monitor_bounds.py -v
"""

from collections import deque

import pytest

from tracker_app.tracking import activity_monitor
from tracker_app.tracking.activity_monitor import ActivityMonitor


class _NullSession:
    def __enter__(self):
        return None

    def __exit__(self, *_args):
        return False


class _StubAnalytics:
    def __init__(self):
        self.logged = []

    def log_session(self, start_time, end_time, concepts_count,
                    avg_attention, primary_activity):
        self.logged.append(avg_attention)

    def get_daily_summary(self, *args, **kwargs):
        return {}

    def get_trend_analysis(self, *args, **kwargs):
        return {}


@pytest.fixture
def monitor(monkeypatch):
    monkeypatch.setattr(activity_monitor, "SessionLocal", _NullSession)
    monkeypatch.setattr(
        activity_monitor.TrackingRepository,
        "log_intent_prediction",
        lambda db, pred: None,
    )
    return ActivityMonitor()


def test_prediction_buffer_is_bounded_deque(monitor):
    assert isinstance(monitor.validator.prediction_buffer, deque)
    for i in range(150):
        monitor.validator.log_prediction(f"intent_{i}", 0.5)
    assert len(monitor.validator.prediction_buffer) == 100
    assert monitor.validator.prediction_buffer[0]["intent"] == "intent_50"


def test_attention_scores_use_constant_memory(monitor):
    monitor.start_session()
    monitor.update_attention(50.0)
    monitor.update_attention(70.0)
    monitor.update_attention(90.0)

    assert not hasattr(monitor, "session_attention_scores")
    stats = monitor.get_session_stats()
    assert stats["avg_attention"] == 70.0


def test_end_session_reports_running_mean(monitor):
    monitor.analytics = _StubAnalytics()
    monitor.start_session()
    for value in [40.0, 60.0, 80.0]:
        monitor.update_attention(value)

    monitor.end_session()

    assert monitor.analytics.logged == [60.0]
