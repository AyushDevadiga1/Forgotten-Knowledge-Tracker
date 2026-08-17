"""Shared Study Session state — the single source of truth for the Start/Stop toggle.

The dashboard (web process) writes this state; the tracking loop (tracker
process) reads it once per cycle. A small JSON file in DATA_DIR is used so the
two processes share one value without any IPC plumbing. The file is written
atomically (tmp + replace) and tolerates missing/corrupt contents by falling
back to "inactive", so a stale file never blocks tracking.

Cross-process safety is provided by a filelock.FileLock sidecar file
(session_state.json.lock). If the lock cannot be created or acquired,
the module falls back to unlocked access with a warning.
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path

from filelock import FileLock, Timeout as LockTimeout
from tracker_app.config import DATA_DIR

_log = logging.getLogger(__name__)

_STATE_PATH = DATA_DIR / "session_state.json"
_LOCK_PATH = DATA_DIR / "session_state.json.lock"
_lock = threading.Lock()
_file_lock = FileLock(_LOCK_PATH, timeout=5)

_DEFAULT = {"active": False, "started_at": None, "stopped_at": None}


def _load() -> dict:
    try:
        with open(_STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return dict(_DEFAULT)


def _save(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _STATE_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    tmp.replace(_STATE_PATH)


def _acquire_file_lock():
    """Acquire the cross-process file lock, falling back on failure."""
    try:
        _file_lock.acquire()
        return True
    except (LockTimeout, OSError) as exc:
        _log.warning(
            "Could not acquire session_state file lock: %s; "
            "proceeding without cross-process safety", exc
        )
        return False


def _release_file_lock(acquired: bool) -> None:
    if acquired:
        try:
            _file_lock.release()
        except Exception:
            pass


def is_active() -> bool:
    """Return True when a study session is currently toggled on."""
    with _lock:
        acquired = _acquire_file_lock()
        try:
            return bool(_load().get("active"))
        finally:
            _release_file_lock(acquired)


def start() -> dict:
    """Toggle a study session on (idempotent). Returns the new state.

    started_at is always stamped with the current time, so a session
    restarted after stop() (or after a crash that left active=true in the
    file) starts a fresh clock rather than counting elapsed time from the
    previous session's start.
    """
    with _lock:
        acquired = _acquire_file_lock()
        try:
            state = _load()
            now = datetime.utcnow().isoformat()
            state["active"] = True
            state["started_at"] = now
            state["stopped_at"] = None
            _save(state)
            return state
        finally:
            _release_file_lock(acquired)


def stop() -> dict:
    """Toggle a study session off (idempotent). Returns the new state."""
    with _lock:
        acquired = _acquire_file_lock()
        try:
            state = _load()
            state["active"] = False
            state["stopped_at"] = datetime.utcnow().isoformat()
            _save(state)
            return state
        finally:
            _release_file_lock(acquired)


def get_status() -> dict:
    """Return the current state plus a live elapsed-seconds figure."""
    with _lock:
        acquired = _acquire_file_lock()
        try:
            state = _load()
        finally:
            _release_file_lock(acquired)
    elapsed = None
    if state.get("active") and state.get("started_at"):
        try:
            started = datetime.fromisoformat(state["started_at"])
            elapsed = int((datetime.utcnow() - started).total_seconds())
        except Exception:
            elapsed = None
    return {
        "active": bool(state.get("active")),
        "started_at": state.get("started_at"),
        "stopped_at": state.get("stopped_at"),
        "elapsed_seconds": elapsed,
    }
