"""Regression tests: export_tracking_data() must not crash on a
bare filename with no directory component.

Finding: activity_monitor.py exported via
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
and a bare filename like "export.json" yields dirname '' -> makedirs('') ->
FileNotFoundError. The fix guards the parent-directory creation.

Run: python -m pytest tracker_app/tests/test_export_tracking_data.py -v
"""

import json
import types

import pytest

from tracker_app.tracking import activity_monitor
from tracker_app.tracking.activity_monitor import ActivityMonitor


class _NullSession:
    def __enter__(self):
        return None

    def __exit__(self, *_args):
        return False


@pytest.fixture
def monitor(monkeypatch):
    monkeypatch.setattr(activity_monitor, "SessionLocal", _NullSession)
    monitor = ActivityMonitor()
    monitor.scheduler = types.SimpleNamespace(get_due_concepts=lambda limit: [])
    monitor.validator = types.SimpleNamespace(get_accuracy_stats=lambda: {})
    monitor.analytics = types.SimpleNamespace(
        get_daily_summary=lambda: {},
        get_trend_analysis=lambda days: {},
    )
    monitor.get_session_stats = lambda: {}
    return monitor


def test_export_accepts_bare_filename(monitor, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = "tracking_export.json"
    monitor.export_tracking_data(target)
    assert tmp_path.joinpath(target).exists()
    with open(target, encoding="utf-8") as f:
        assert json.load(f)["session_stats"] == {}


def test_export_creates_nested_parent_directory(monitor, tmp_path):
    target = str(tmp_path / "nested" / "deep" / "out.json")
    monitor.export_tracking_data(target)
    assert tmp_path.joinpath("nested", "deep", "out.json").exists()


def test_export_returns_data(monitor, tmp_path):
    data = monitor.export_tracking_data(str(tmp_path / "out.json"))
    assert data["session_stats"] == {}
    assert data["due_concepts"] == []
