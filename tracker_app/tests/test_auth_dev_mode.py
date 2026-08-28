"""Regression tests for the C-1 auth dev-mode contract.

Covers two defects: the shared web gate ignoring NO_AUTH, and config.py
appending a freshly generated API_KEY to .env on every missing-key boot.

Run: python -m pytest tracker_app/tests/test_auth_dev_mode.py -v
"""

import os
import subprocess
import sys
from pathlib import Path

from tracker_app import config as cfg
from tracker_app.web.app import app
from tracker_app.web.shared import check_api_key


def _test_client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app.test_client()


def test_shared_gate_allows_dev_mode_when_key_present(monkeypatch):
    """NO_AUTH=true must bypass shared.check_api_key even when an API_KEY is
    present in the environment (mirrors conftest's empty-key precedent but
    exercises the NO_AUTH path of the gate)."""
    monkeypatch.setenv("NO_AUTH", "true")
    monkeypatch.setenv("API_KEY", "sekrit")
    resp = _test_client().get("/api/v1/session/status")
    assert resp.status_code == 200


def test_shared_gate_still_enforces_auth_without_no_auth(monkeypatch):
    """Without NO_AUTH, an API_KEY in the environment keeps the gate strict:
    a request with no key must still be rejected 401 by the shared gate."""
    monkeypatch.setenv("API_KEY", "sekrit")
    monkeypatch.delenv("NO_AUTH", raising=False)
    resp = _test_client().get("/api/v1/session/status")
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Unauthorized"


def test_check_api_key_returns_none_inside_request_when_no_auth_true(monkeypatch):
    monkeypatch.setenv("NO_AUTH", "true")
    monkeypatch.setenv("API_KEY", "sekrit")
    with app.test_request_context("/api/v1/session/status"):
        assert check_api_key() is None


def test_config_does_not_persist_api_key_when_no_auth_true(tmp_path):
    """Importing config with NO_AUTH=true and no API_KEY must leave the env
    file byte-for-byte unchanged and the env var unset (no append churn).

    Runs in a subprocess against an isolated copy of config.py so the real,
    gitignored .env is never touched.
    """
    src = Path(cfg.__file__).read_text(encoding="utf-8")
    isolated_pkg = tmp_path / "tracker_app"
    isolated_pkg.mkdir()
    (isolated_pkg / "__init__.py").write_text("", encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET_KEY=static-test-secret-1234567890abcdef\n", encoding="utf-8")

    env_file_literal = str(env_file).replace("\\", "/")
    modified = src.replace(
        '_ENV_FILE = Path(__file__).parent.parent / ".env"',
        '_ENV_FILE = Path("{}")'.format(env_file_literal),
    )
    (isolated_pkg / "config.py").write_text(modified, encoding="utf-8")

    code = "\n".join(
        [
            "import os, sys, pathlib",
            "sys.path.insert(0, '{}')".format(str(tmp_path).replace("\\", "/")),
            "os.environ.pop('API_KEY', None)",
            "os.environ['NO_AUTH'] = 'true'",
            "os.environ.pop('SECRET_KEY', None)",
            "os.environ.pop('DEBUG', None)",
            "before = pathlib.Path('{}').read_text(encoding='utf-8')".format(env_file_literal),
            "import tracker_app.config as c",
            "assert 'API_KEY' not in os.environ, 'API_KEY set in env while NO_AUTH=true'",
            "after = pathlib.Path(str(c._ENV_FILE)).read_text(encoding='utf-8')",
            "assert before == after, 'config mutated the environment file'",
            "api_lines = [ln for ln in after.splitlines() if ln.startswith('API_KEY=')]",
            "assert not api_lines, 'config appended API_KEY lines: {}'.format(api_lines)",
            "print('OK: env file unchanged')",
        ]
    )
    env = {k: v for k, v in os.environ.items() if k not in ("API_KEY", "SECRET_KEY", "DEBUG", "NO_AUTH")}
    r = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(Path.cwd()),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, "config no-persist contract broken: {}".format(r.stderr)
    assert "OK: env file unchanged" in r.stdout
