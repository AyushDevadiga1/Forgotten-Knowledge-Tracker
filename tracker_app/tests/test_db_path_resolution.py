"""Regression tests for FKT-F-001: FKT_TEST_DB / engine rebinding contract.

The documented contract in tracker_app/db/models.py — "tests can safely set
FKT_TEST_DB at the top of a test file and get the correct DB path" — was false
in-process: config.DB_PATH was frozen at import time, and module-scope
importers (`from tracker_app.db.models import SessionLocal`) captured a lazy
proxy that always forwarded to the module-global `_SessionLocal`, silently
bypassing test patching of models.SessionLocal / models.engine.

These tests pin the fixed behavior:
  - get_db_path() reflects a later os.environ['FKT_TEST_DB'] change;
  - get_engine() re-reads the env at call time (no import-order dependence);
  - a module-scope importer of SessionLocal honors a later rebinding of
    models.SessionLocal (row lands in the rebound engine's DB, not the
    env-bound DB — two throwaway temp DBs);
  - a proxy captured via `models.engine` honors a later rebinding of
    models.engine.

Note: no module-level FKT_TEST_DB is set here on purpose — the whole point is
that a later env change (or rebind) must be honored, so every test drives the
change after imports via monkeypatch (test_api.py patching style).

Run: python -m pytest tracker_app/tests/test_db_path_resolution.py -v
"""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from tracker_app import config
from tracker_app.db.models import Base, TrackedConcept, get_engine


def _db_path(tmp_path, name):
    return str(tmp_path / name)


def _concept_rows(db_file, concept="f001-probe"):
    """Return matching concept rows from a plain sqlite file DB ([] = none)."""
    engine = create_engine(f"sqlite:///{db_file}")
    try:
        with engine.connect() as conn:
            return [
                row[0]
                for row in conn.execute(
                    text("SELECT concept FROM tracked_concepts WHERE concept = :c"),
                    {"c": concept},
                ).fetchall()
            ]
    finally:
        engine.dispose()


def test_get_db_path_reflects_later_env_change(monkeypatch):
    default = str(config.DATA_DIR / "sessions.db")
    monkeypatch.delenv("FKT_TEST_DB", raising=False)
    assert config.get_db_path() == default

    monkeypatch.setenv("FKT_TEST_DB", "C:\\somewhere\\else\\sessions.db")
    assert config.get_db_path() == "C:\\somewhere\\else\\sessions.db"


def test_get_engine_reads_env_at_call_time(monkeypatch, tmp_path):
    """Claim 1 of the finding: env set AFTER import must be honored."""
    import tracker_app.db.models as models

    first = _db_path(tmp_path, "f001_first.db")
    second = _db_path(tmp_path, "f001_second.db")

    monkeypatch.setattr(models, "_engine", None)
    monkeypatch.setenv("FKT_TEST_DB", first)
    engine1 = get_engine()
    try:
        assert os.path.normcase(engine1.url.database) == os.path.normcase(first)
    finally:
        engine1.dispose()

    # env changed after the engine machinery was already exercised
    monkeypatch.setenv("FKT_TEST_DB", second)
    monkeypatch.setattr(models, "_engine", None)
    engine2 = get_engine()
    try:
        assert os.path.normcase(engine2.url.database) == os.path.normcase(second)
    finally:
        engine2.dispose()


def test_session_rebind_honored_by_module_scope_importer(monkeypatch, tmp_path):
    """Claim 2 of the finding: an import-time capture of the SessionLocal proxy
    must honor a later rebinding of models.SessionLocal."""
    import tracker_app.db.models as models

    env_db = _db_path(tmp_path, "f001_env_a.db")
    rebound_db = _db_path(tmp_path, "f001_rebound_b.db")

    # Env-bound control: without the fix, the write would land here (or in the
    # frozen DB_PATH), never in the rebound engine's DB.
    monkeypatch.setenv("FKT_TEST_DB", env_db)
    monkeypatch.setattr(models, "_engine", None)
    monkeypatch.setattr(models, "_SessionLocal", None)

    engine_a = create_engine(f"sqlite:///{env_db}")
    engine_b = create_engine(f"sqlite:///{rebound_db}")
    try:
        Base.metadata.create_all(bind=engine_a)
        Base.metadata.create_all(bind=engine_b)

        # Reproduce the module-scope import-time capture: the importer holds
        # the proxy, NOT whatever models.SessionLocal is later rebound to.
        proxy = models.SessionLocal
        from tracker_app.learning import concept_scheduler as cs_mod
        assert cs_mod.SessionLocal is proxy

        # Rebind AFTER the capture.
        sm_b = sessionmaker(bind=engine_b)
        monkeypatch.setattr(models, "SessionLocal", sm_b)

        with cs_mod.SessionLocal() as db:
            assert db.bind is engine_b  # delegated to the rebound sessionmaker
            db.add(TrackedConcept(concept="f001-probe"))
            db.commit()

        assert _concept_rows(rebound_db) == ["f001-probe"]
        assert _concept_rows(env_db) == []
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_engine_rebind_honored_by_captured_proxy(monkeypatch, tmp_path):
    """A proxy captured via `models.engine` must honor a later rebinding of
    models.engine (e.g. Base.metadata.create_all(bind=engine) in db_module.py)."""
    import tracker_app.db.models as models

    default_url = get_engine().url  # whatever the default/env-bound engine is
    captured = models.engine        # the lazy proxy, as captured at import time
    rebound = create_engine(f"sqlite:///{_db_path(tmp_path, 'f001_engine.db')}")
    try:
        monkeypatch.setattr(models, "engine", rebound)

        assert captured.url == rebound.url   # proxy re-resolves the rebind
        assert captured.url != default_url   # genuinely the other engine
        assert models.engine.url == rebound.url  # direct access hits the rebind
    finally:
        rebound.dispose()
