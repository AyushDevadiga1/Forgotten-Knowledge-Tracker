"""Tests for the shared study-session state (Phase 9 session-gated capture)."""

import pytest

from tracker_app.tracking import session_state as ss


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """Point the session-state file at a temp path for the duration of a test."""
    state_file = tmp_path / "session_state.json"
    monkeypatch.setattr(ss, "_STATE_PATH", state_file)
    return state_file


def test_default_is_inactive(isolated_state):
    assert ss.is_active() is False


def test_start_activates_session(isolated_state):
    result = ss.start()
    assert result["active"] is True
    assert result["started_at"] is not None
    assert ss.is_active() is True


def test_stop_deactivates_session(isolated_state):
    ss.start()
    result = ss.stop()
    assert result["active"] is False
    assert result["stopped_at"] is not None
    assert ss.is_active() is False


def test_start_stop_idempotent(isolated_state):
    ss.start()
    ss.start()
    assert ss.is_active() is True
    ss.stop()
    ss.stop()
    assert ss.is_active() is False


def test_status_reports_elapsed_seconds(isolated_state):
    ss.start()
    status = ss.get_status()
    assert status["active"] is True
    assert isinstance(status["elapsed_seconds"], int)
    assert status["elapsed_seconds"] >= 0


def test_state_persists_to_disk(isolated_state):
    ss.start()
    assert isolated_state.exists()
    # A "fresh process" reload (module functions read the file on every call).
    assert ss.is_active() is True


def test_externally_written_state_is_read(isolated_state):
    isolated_state.write_text('{"active": true, "started_at": "2026-01-01T00:00:00"}', encoding="utf-8")
    assert ss.is_active() is True
    status = ss.get_status()
    assert status["active"] is True
    assert status["started_at"] == "2026-01-01T00:00:00"


def test_corrupt_state_file_falls_back_to_inactive(isolated_state):
    isolated_state.write_text("not json {{{", encoding="utf-8")
    assert ss.is_active() is False
    assert ss.get_status()["active"] is False


def test_intent_gate_default_allows_studying_only():
    from tracker_app.config import SESSION_ALLOWED_INTENTS
    assert "studying" in SESSION_ALLOWED_INTENTS
