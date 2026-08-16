"""Regression tests for FKT-F-006: feedback_training_samples.timestamp has
exactly one index on every provisioning path.

Finding: migration 004 created `ix_feedback_samples_timestamp` on
feedback_training_samples(timestamp), while the ORM model's index=True
(models.py FeedbackTrainingSample.timestamp) auto-creates
`ix_feedback_training_samples_timestamp` for the same column. Because the
migration runner runs ensure_base_schema (create_all) before migration 004 and
the index names differ, `IF NOT EXISTS` cannot dedupe them — migrated
databases ended up with two indexes on the same column (write amplification on
every insert; schema diverged by init path). All other 7 migration-004 index
names match the ORM auto-names exactly; this one was the sole outlier.

The fix: migration 012_drop_duplicate_feedback_index executes
`DROP INDEX IF EXISTS ix_feedback_samples_timestamp`, converging every path to
the single ORM-managed index. These tests pin:
  - a fresh DB after run_migrations has exactly one index on the column,
    `ix_feedback_training_samples_timestamp` (legacy name absent);
  - a DB that already carries both indexes converges to the single index after
    run_migrations, and a second run is a no-op (idempotent).

All DBs are throwaway tmp_path files; tracker_app/data/sessions.db is guarded
(size/mtime snapshot before and after) and never touched.

Run: python -m pytest tracker_app/tests/test_duplicate_feedback_index.py -v
"""

import sqlite3
from pathlib import Path

from tracker_app.db.migrations import ensure_base_schema, run_migrations

# Total migration count tracks the MIGRATIONS registry in
# tracker_app/db/migrations.py — bump when a migration is appended
# (currently 13: 001..013 including 012_drop_duplicate_feedback_index and
# 013_feedback_used_in_training).
TOTAL_MIGRATIONS = 13

# The single index the ORM auto-creates for FeedbackTrainingSample.timestamp
# (declarative_base() default naming: "ix_<table>_<column>").
ORM_INDEX = "ix_feedback_training_samples_timestamp"
# The legacy migration-004 index that migration 012 must drop.
LEGACY_INDEX = "ix_feedback_samples_timestamp"

# The real production DB, which these tests must never open or modify.
_REAL_DB = Path(__file__).resolve().parents[2] / "tracker_app" / "data" / "sessions.db"


def _indexes_on(db_file, table="feedback_training_samples"):
    """Return the names of all indexes on `table`, sorted."""
    conn = sqlite3.connect(db_file)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=? ORDER BY name",
            (table,),
        ).fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()


def _real_db_snapshot():
    """(size, mtime_ns) of the production DB, or None if it does not exist."""
    if not _REAL_DB.exists():
        return None
    stat = _REAL_DB.stat()
    return (stat.st_size, stat.st_mtime_ns)


def _assert_real_db_untouched(before):
    after = _real_db_snapshot()
    assert after == before, (
        f"tracker_app/data/sessions.db changed during the test: {before} -> {after}"
    )


def test_fresh_migrated_db_has_single_feedback_index(tmp_path):
    db_file = str(tmp_path / "fresh.db")
    real_before = _real_db_snapshot()
    try:
        result = run_migrations(db_path=db_file)
        assert result["applied"] == TOTAL_MIGRATIONS
        assert result["failed"] == 0
        assert result["errors"] == []

        indexes = _indexes_on(db_file)
        assert indexes == [ORM_INDEX], f"expected only {ORM_INDEX!r}, got {indexes}"
        assert LEGACY_INDEX not in indexes
    finally:
        _assert_real_db_untouched(real_before)


def test_duplicate_index_converges_after_run_migrations(tmp_path):
    db_file = str(tmp_path / "duplicate.db")
    real_before = _real_db_snapshot()
    try:
        # Simulate a pre-fix migrated database: create_all brought the ORM
        # index, and migration 004 added the differently-named legacy one.
        ensure_base_schema(db_file)
        conn = sqlite3.connect(db_file)
        try:
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_feedback_samples_timestamp "
                "ON feedback_training_samples (timestamp)"
            )
            conn.commit()
        finally:
            conn.close()

        pre = _indexes_on(db_file)
        assert set(pre) == {ORM_INDEX, LEGACY_INDEX}, f"precondition failed: {pre}"

        # run_migrations drops the legacy index (all 12 apply on a fresh
        # schema_migrations), then a second pass is a pure no-op.
        first = run_migrations(db_path=db_file)
        assert first["applied"] == TOTAL_MIGRATIONS
        assert first["failed"] == 0
        assert first["errors"] == []
        assert _indexes_on(db_file) == [ORM_INDEX]

        second = run_migrations(db_path=db_file)
        assert second["applied"] == 0
        assert second["skipped"] == TOTAL_MIGRATIONS
        assert second["failed"] == 0
        assert second["errors"] == []
        assert _indexes_on(db_file) == [ORM_INDEX]
    finally:
        _assert_real_db_untouched(real_before)
