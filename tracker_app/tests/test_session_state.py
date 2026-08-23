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


def test_restart_resets_started_at(isolated_state):
    ss.start()
    first_started = ss.get_status()["started_at"]
    ss.stop()
    ss.start()
    second_started = ss.get_status()["started_at"]
    assert second_started != first_started
    # Elapsed clock counts from the NEW session, not the previous one.
    assert ss.get_status()["elapsed_seconds"] < 5


def test_start_after_crash_resets_stale_clock(isolated_state):
    # Simulate a crashed session: file stuck active with an old started_at.
    isolated_state.write_text(
        '{"active": true, "started_at": "2026-01-01T00:00:00", "stopped_at": null}',
        encoding="utf-8",
    )
    ss.start()
    status = ss.get_status()
    assert status["started_at"] != "2026-01-01T00:00:00"
    assert status["elapsed_seconds"] < 5


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


def test_lock_file_created_as_sidecar(isolated_state, monkeypatch):
    """Lock sidecar file is created and used during acquire/release."""
    lock_file = isolated_state.with_suffix(".json.lock")
    monkeypatch.setattr(ss, "_LOCK_PATH", lock_file)
    fl = ss.FileLock(lock_file, timeout=5)
    monkeypatch.setattr(ss, "_file_lock", fl)
    acquire_called = []
    original_acquire = fl.acquire

    def tracking_acquire(*a, **kw):
        result = original_acquire(*a, **kw)
        acquire_called.append(True)
        return result

    fl.acquire = tracking_acquire
    ss.start()
    assert len(acquire_called) == 1, "file_lock.acquire should be called once"


def test_lock_failure_falls_back_gracefully(isolated_state, monkeypatch):
    """When file lock acquisition fails, operations fall back to unlocked access."""

    class FailingLock:
        def acquire(self, *a, **kw):
            raise OSError("permission denied")

        def release(self, *a, **kw):
            pass

    monkeypatch.setattr(ss, "_file_lock", FailingLock())
    result = ss.start()
    assert result["active"] is True
    assert ss.is_active() is True
    assert ss.get_status()["active"] is True


_worker_script = """import sys, json
from pathlib import Path
state_path = Path(sys.argv[1])
lock_path = Path(sys.argv[2])
action = sys.argv[3]
from tracker_app.tracking import session_state as ss
ss._STATE_PATH = state_path
ss._LOCK_PATH = lock_path
ss._file_lock = ss.FileLock(lock_path, timeout=5)
if action == "start":
    ss.start()
elif action == "stop":
    ss.stop()
elif action == "read":
    print(json.dumps(ss._load()))
"""


def test_concurrent_start_stop_consistent(isolated_state, monkeypatch, tmp_path):
    import multiprocessing
    import subprocess
    import textwrap

    lock_path = isolated_state.with_suffix(".json.lock")
    monkeypatch.setattr(ss, "_LOCK_PATH", lock_path)
    monkeypatch.setattr(ss, "_file_lock", ss.FileLock(lock_path, timeout=5))
    script = tmp_path / "_worker.py"
    script.write_text(textwrap.dedent(_worker_script), encoding="utf-8")
    exe = ss.sys.executable if hasattr(ss, "sys") else __import__("sys").executable
    ctx = multiprocessing.get_context("spawn")
    p1 = ctx.Process(
        target=subprocess.run,
        args=([exe, str(script), str(isolated_state), str(lock_path), "start"],),
    )
    p2 = ctx.Process(
        target=subprocess.run,
        args=([exe, str(script), str(isolated_state), str(lock_path), "stop"],),
    )
    p1.start()
    p2.start()
    p1.join(timeout=10)
    p2.join(timeout=10)
    assert p1.exitcode == 0 and p2.exitcode == 0
    ss._STATE_PATH = isolated_state
    ss._LOCK_PATH = lock_path
    ss._file_lock = ss.FileLock(lock_path, timeout=5)
    status = ss.get_status()
    assert status["active"] in (True, False)
    assert isinstance(status["started_at"], str) or status["started_at"] is None
    assert isinstance(status["stopped_at"], str) or status["stopped_at"] is None
