from pathlib import Path

"""Regression tests for C-1 (auth/SECRET_KEY contract) and C-2 (single
concurrent retraining run).

Run: python -m pytest tracker_app/tests/test_security_contract.py -v
"""

import os
import subprocess
import sys
import threading


def test_app_import_generates_secret_key_when_missing():
    """C-1: when SECRET_KEY is missing, config.py auto-generates one
    and writes it to .env so the app always starts securely."""
    root = str(Path(__file__).parent.parent.parent)
    env = {k: v for k, v in os.environ.items() if k not in ("SECRET_KEY", "DEBUG")}
    r = subprocess.run(
        [
            sys.executable,
            "-c",
            'import tracker_app.config; import tracker_app.web.app; import os; print(len(os.environ["SECRET_KEY"]))',
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, f"App failed to start: {r.stderr}"
    # Verify a real key was generated (not the dev default)
    key_len = int(r.stdout.strip())
    assert key_len >= 32, f"SECRET_KEY not auto-generated (len={key_len})"


def test_app_import_always_has_valid_secret_key(tmp_path):
    """C-1: whether DEBUG is set or not, the app must always have a
    valid SECRET_KEY (auto-generated if missing from env)."""
    root = str(Path(__file__).parent.parent.parent)
    env = {k: v for k, v in os.environ.items() if k not in ("SECRET_KEY",)}
    r = subprocess.run(
        [sys.executable, "-c", 'import tracker_app.web.app; print(len(tracker_app.web.app.app.config["SECRET_KEY"]))'],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, f"App failed: {r.stderr}"
    key_len = int(r.stdout.strip())
    assert key_len >= 32, f"SECRET_KEY too short ({key_len} chars)"


def test_auth_enforced_when_no_auth_false_and_key_set(monkeypatch):
    """C-1: with NO_AUTH=false and API_KEY set, the before_request hook must
    require X-API-Key (401 missing, 403 wrong, 404 once authenticated)."""
    import tracker_app.web.auth as auth
    from tracker_app.web.app import app

    monkeypatch.setattr(auth, "_NO_AUTH", False)
    monkeypatch.setattr(auth, "_API_KEY", "sekrit")
    app.config["TESTING"] = True
    client = app.test_client()

    resp = client.get("/api/v1/session/status")
    assert resp.status_code == 401

    resp = client.get("/api/v1/session/status", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 403

    resp = client.get("/api/v1/session/status", headers={"X-API-Key": "sekrit"})
    assert resp.status_code == 200


def test_auth_skipped_when_no_auth_true(monkeypatch):
    import tracker_app.web.auth as auth
    from tracker_app.web.app import app

    monkeypatch.setattr(auth, "_NO_AUTH", True)
    monkeypatch.setattr(auth, "_API_KEY", "sekrit")
    app.config["TESTING"] = True
    resp = app.test_client().get("/api/v1/session/status")
    assert resp.status_code == 200  # not blocked by auth


def test_retrain_lock_allows_single_concurrent_run(monkeypatch):
    """C-2: two near-simultaneous triggers must start at most one retraining
    subprocess (the second skips while the first holds the lock)."""
    import tracker_app.web.api as api_mod
    from tracker_app.db import repository as repo_mod

    monkeypatch.setattr(repo_mod.FeedbackRepository, "get_total_count", lambda db: 50)
    starts = []
    monkeypatch.setattr(
        api_mod.FeedbackService,
        "_retrain_from_feedback",
        staticmethod(lambda: starts.append(threading.current_thread().name)),
    )

    fresh_lock = threading.Lock()
    monkeypatch.setattr(api_mod, "_retrain_lock", fresh_lock)

    api_mod.FeedbackService.maybe_trigger_retrain()
    api_mod.FeedbackService.maybe_trigger_retrain()

    assert len(starts) == 1


def test_socketio_cors_is_not_wildcard():
    """Socket.IO cors_allowed_origins must be restricted to localhost.

    A wildcard allows any website to connect to localhost:5000 and receive
    micro_quiz broadcasts and stats_update events, leaking study data.
    """
    source = Path(__file__).resolve().parents[1] / "web" / "realtime.py"
    text = source.read_text(encoding="utf-8")
    assert 'cors_allowed_origins="*"' not in text, "Socket.IO must not use wildcard CORS origin"
    assert "cors_allowed_origins" in text
