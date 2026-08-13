"""Regression tests for FKT-F-002: init_all_databases() applies migrations.

Finding: run_migrations() was never wired into any runtime startup path.
init_all_databases() only ran Base.metadata.create_all, and create_all never
ALTERs existing tables. A database created by an older FKT version (missing
migration-only columns such as intent_predictions.prompted_at / window_title)
crashed with "table intent_predictions has no column named prompted_at" on the
first ORM write (api.py:426-434 prompted_at claim UPDATE, etc.).

The fix: init_all_databases() calls run_migrations(db_path=get_db_path()) after
init_db() — create_all stays create_all-only. These tests pin:
  - a stale-schema DB (intent_predictions built via raw sqlite3 DDL, pre-007/008)
    converges after init_all_databases(): schema_migrations exists with all 11
    entries, the ORM can INSERT an IntentPrediction (including the migration-only
    columns), and the api.py prompted_at claim UPDATE succeeds;
  - an already-migrated DB is a no-op: a second init_all_databases() applies
    nothing (run_migrations reports applied=0, skipped=11).

All DBs are throwaway tmp_path files; the real data/sessions.db is never touched.

Run: python -m pytest tracker_app/tests/test_migrations_at_startup.py -v
"""

import sqlite3
from datetime import datetime

from sqlalchemy import update

import tracker_app.db.models as models
from tracker_app.db.db_module import init_all_databases
from tracker_app.db.migrations import run_migrations
from tracker_app.db.models import IntentPrediction

# Old-version intent_predictions: identical shape to the pre-007/008 table —
# no prompted_at, no window_title (bug-reproducer probe 1 DDL).
_STALE_INTENT_PREDICTIONS_DDL = """
CREATE TABLE intent_predictions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           TEXT    NOT NULL,
    predicted_intent    TEXT,
    confidence          REAL,
    context_keywords    TEXT,
    user_feedback       INTEGER,
    actual_intent       TEXT,
    feedback_timestamp  TEXT
)
"""

# Total migration count tracks the MIGRATIONS registry in
# tracker_app/db/migrations.py — bump when a migration is appended
# (currently 12: 001..012 including 011_datetime_storage_format and
# 012_drop_duplicate_feedback_index).
TOTAL_MIGRATIONS = 12


def _create_stale_db(db_file):
    """Build a pre-migration database with only the old intent_predictions table."""
    conn = sqlite3.connect(db_file)
    try:
        conn.execute(_STALE_INTENT_PREDICTIONS_DDL)
        conn.commit()
    finally:
        conn.close()


def _use_db(monkeypatch, db_file):
    """Point the lazy ORM engine/session machinery at db_file.

    get_engine()/get_session_local() cache _engine/_SessionLocal globally, so
    tests must reset them (and set FKT_TEST_DB, which get_db_path() re-reads at
    call time) for init_all_databases() to target the throwaway DB.
    """
    monkeypatch.setenv("FKT_TEST_DB", db_file)
    monkeypatch.setattr(models, "_engine", None)
    monkeypatch.setattr(models, "_SessionLocal", None)


def _release_engine():
    """Close pooled connections so tmp_path cleanup can delete the file."""
    engine = models._engine
    if engine is not None:
        engine.dispose()
    models._engine = None
    models._SessionLocal = None


def _applied_migration_ids(db_file):
    conn = sqlite3.connect(db_file)
    try:
        return [
            row[0]
            for row in conn.execute("SELECT id FROM schema_migrations ORDER BY id")
        ]
    finally:
        conn.close()


def test_init_all_databases_converges_stale_schema(monkeypatch, tmp_path):
    db_file = str(tmp_path / "stale.db")
    _create_stale_db(db_file)
    _use_db(monkeypatch, db_file)
    try:
        init_all_databases()

        # 1. schema_migrations exists and records every migration.
        assert len(_applied_migration_ids(db_file)) == TOTAL_MIGRATIONS

        # 2. ORM INSERT including the migration-only columns now succeeds
        #    (before the fix: OperationalError, no column named prompted_at).
        session = models.get_session_local()()
        try:
            row = IntentPrediction(
                timestamp=datetime.utcnow(),
                predicted_intent="studying",
                confidence=0.9,
                context_keywords="[]",
                prompted_at=None,
                window_title="pytest window",
            )
            session.add(row)
            session.commit()

            # 3. api.py:426-434 prompted_at claim UPDATE works against the
            #    migrated table (before the fix: "no such column: prompted_at").
            now = datetime.utcnow()
            result = session.execute(
                update(IntentPrediction)
                .where(
                    IntentPrediction.id == row.id,
                    IntentPrediction.prompted_at.is_(None),
                    IntentPrediction.user_feedback.is_(None),
                )
                .values(prompted_at=now)
            )
            session.commit()
            assert result.rowcount == 1

            got = session.query(IntentPrediction).filter_by(id=row.id).one()
            assert got.prompted_at is not None
            assert got.window_title == "pytest window"
        finally:
            session.close()
    finally:
        _release_engine()


def test_init_all_databases_idempotent_on_migrated_db(monkeypatch, tmp_path):
    db_file = str(tmp_path / "migrated.db")
    _use_db(monkeypatch, db_file)
    try:
        # First startup run converges the fresh DB (applies all 10).
        init_all_databases()
        assert len(_applied_migration_ids(db_file)) == TOTAL_MIGRATIONS

        # Second startup run must be a no-op: nothing new applied, all skipped.
        init_all_databases()

        result = run_migrations(db_path=db_file)
        assert result["applied"] == 0
        assert result["skipped"] == TOTAL_MIGRATIONS
        assert result["failed"] == 0
        assert result["errors"] == []
        assert len(_applied_migration_ids(db_file)) == TOTAL_MIGRATIONS
    finally:
        _release_engine()
