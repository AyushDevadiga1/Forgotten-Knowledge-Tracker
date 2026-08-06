"""Shared Study Session state — the single source of truth for the Start/Stop toggle.

The dashboard (web process) writes this state; the tracking loop (tracker
process) reads it once per cycle. A small JSON file in DATA_DIR is used so the
two processes share one value without any IPC plumbing. The file is written
atomically (tmp + replace) and tolerates missing/corrupt contents by falling
back to "inactive", so a stale file never blocks tracking.
"""

import json
import threading
from datetime import datetime
from pathlib import Path

from tracker_app.config import DATA_DIR

_STATE_PATH = DATA_DIR / "session_state.json"
_lock = threading.Lock()

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


def is_active() -> bool:
    """Return True when a study session is currently toggled on."""
    with _lock:
        return bool(_load().get("active"))


def start() -> dict:
    """Toggle a study session on (idempotent). Returns the new state."""
    with _lock:
        state = _load()
        now = datetime.now().isoformat()
        state["active"] = True
        if not state.get("started_at"):
            state["started_at"] = now
        state["stopped_at"] = None
        _save(state)
        return state


def stop() -> dict:
    """Toggle a study session off (idempotent). Returns the new state."""
    with _lock:
        state = _load()
        state["active"] = False
        state["stopped_at"] = datetime.now().isoformat()
        _save(state)
        return state


def get_status() -> dict:
    """Return the current state plus a live elapsed-seconds figure."""
    with _lock:
        state = _load()
    elapsed = None
    if state.get("active") and state.get("started_at"):
        try:
            started = datetime.fromisoformat(state["started_at"])
            elapsed = int((datetime.now() - started).total_seconds())
        except Exception:
            elapsed = None
    return {
        "active": bool(state.get("active")),
        "started_at": state.get("started_at"),
        "stopped_at": state.get("stopped_at"),
        "elapsed_seconds": elapsed,
    }
