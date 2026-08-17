from pathlib import Path

"""Regression tests for C-1 (auth/SECRET_KEY contract) and C-2 (single
concurrent retraining run).

Run: python -m pytest tracker_app/tests/test_security_contract.py -v
"""

import os
import subprocess
import sys
import threading

import pytest


def test_app_import_raises_without_secret_key_in_production():
    """C-1: the app must refuse to start when SECRET_KEY is missing and
    DEBUG != true, instead of silently falling back to the public dev key."""
    root = str(Path(__file__).parent.parent.parent)
    env = {k: v for k, v in os.environ.items()
           if k not in ('SECRET_KEY', 'DEBUG')}
    r = subprocess.run(
        [sys.executable, '-c', 'import tracker_app.web.app'],
        cwd=root, env=env, capture_output=True, text=True, timeout=120,
    )
    assert r.returncode != 0
    assert 'SECRET_KEY' in r.stderr


def test_app_import_allows_dev_key_when_debug_true(tmp_path):
    """C-1: with DEBUG=true (dev), a missing SECRET_KEY must warn and fall back
    to the dev key instead of raising."""
    root = str(Path(__file__).parent.parent.parent)
    env = {k: v for k, v in os.environ.items()
           if k not in ('SECRET_KEY', 'DEBUG')}
    env['DEBUG'] = 'true'
    r = subprocess.run(
        [sys.executable, '-c', 'import tracker_app.web.app; print(tracker_app.web.app.app.config["SECRET_KEY"])'],
        cwd=root, env=env, capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, r.stderr
    assert 'dev-secret-key-change-in-production' in r.stdout


def test_auth_enforced_when_no_auth_false_and_key_set(monkeypatch):
    """C-1: with NO_AUTH=false and API_KEY set, the before_request hook must
    require X-API-Key (401 missing, 403 wrong, 404 once authenticated)."""
    import tracker_app.web.auth as auth
    from tracker_app.web.app import app

    monkeypatch.setattr(auth, '_NO_AUTH', False)
    monkeypatch.setattr(auth, '_API_KEY', 'sekrit')
    app.config['TESTING'] = True
    client = app.test_client()

    resp = client.get('/api/v1/session/status')
    assert resp.status_code == 401

    resp = client.get('/api/v1/session/status', headers={'X-API-Key': 'wrong'})
    assert resp.status_code == 403

    resp = client.get('/api/v1/session/status', headers={'X-API-Key': 'sekrit'})
    assert resp.status_code == 200


def test_auth_skipped_when_no_auth_true(monkeypatch):
    import tracker_app.web.auth as auth
    from tracker_app.web.app import app

    monkeypatch.setattr(auth, '_NO_AUTH', True)
    monkeypatch.setattr(auth, '_API_KEY', 'sekrit')
    app.config['TESTING'] = True
    resp = app.test_client().get('/api/v1/session/status')
    assert resp.status_code == 200  # not blocked by auth


def test_retrain_lock_allows_single_concurrent_run(monkeypatch):
    """C-2: two near-simultaneous triggers must start at most one retraining
    subprocess (the second skips while the first holds the lock)."""
    import tracker_app.web.api as api_mod
    from tracker_app.db import repository as repo_mod

    monkeypatch.setattr(repo_mod.FeedbackRepository, 'get_total_count',
                        lambda db: 50)
    starts = []
    monkeypatch.setattr(api_mod.FeedbackService, '_retrain_from_feedback',
                        staticmethod(lambda: starts.append(threading.current_thread().name)))

    fresh_lock = threading.Lock()
    monkeypatch.setattr(api_mod, '_retrain_lock', fresh_lock)

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
    assert 'cors_allowed_origins="*"' not in text, (
        "Socket.IO must not use wildcard CORS origin"
    )
    assert 'cors_allowed_origins' in text
