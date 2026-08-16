"""Regression tests for FKT-F-004: DateTime columns must use the ORM's
space-separated storage format everywhere.

Finding: raw-SQL writers (tracker_app/tools/populate.py, preflight_check.py)
stored datetime.isoformat() values ('2026-08-13T09:00:00') into DateTime
columns while the ORM writes and compares space-separated text
('2026-08-13 09:00:00.000000'). Because ' ' < 'T' in ASCII, same-day 'T' rows
sorted lexicographically AFTER the bound datetime and were silently excluded
from due queries (ConceptScheduler.get_due_concepts, LearningRepository
get_items_due/get_stats) until the date flipped. The live DB already had 54
such rows in tracked_concepts.next_review.

The fix: writers emit str(datetime) (space form), and migration
011_datetime_storage_format normalizes already-seeded 'T' rows with a
LIKE-guarded UPDATE (idempotent — after normalization no row matches).

These tests pin:
  - migration 011 converts a seeded 'T' next_review row to space format and
    the due query then includes it at the boundary it was previously excluded
    from (while a genuinely future row stays excluded);
  - migration 011 is a no-op when no 'T' rows exist (applied/skipped counts
    still correct, rows byte-for-byte unchanged);
  - populate.py emits space-formatted values into every affected DateTime
    column (executed against a throwaway DB in a subprocess so the real
    data/sessions.db is never opened).

All DBs are throwaway tmp_path files; data/sessions.db is never touched.

Run: python -m pytest tracker_app/tests/test_datetime_storage_format.py -v
"""

import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import tracker_app.db.models as models
from tracker_app.db.migrations import ensure_base_schema, run_migrations
from tracker_app.learning.concept_scheduler import ConceptScheduler

# ORM/SQLAlchemy SQLite storage form: 'YYYY-MM-DD HH:MM:SS' with optional
# '.ffffff' microseconds. Space at index 10 is what makes same-day ordering
# correct (' ' < 'T').
_SPACE_FORMAT = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$")

# Fixed bound from the FKT-F-004 reproduction: rows due 2026-08-13 09:00 are
# due at this instant; a row due 2026-08-14 is not.
BOUND = datetime(2026, 8, 13, 10, 0, 0)

# Total migration count tracks the MIGRATIONS registry in
# tracker_app/db/migrations.py — bump when a migration is appended
# (currently 13: 001..013 including 011_datetime_storage_format, 012
# drop_duplicate_feedback_index, and 013_feedback_used_in_training).
TOTAL_MIGRATIONS = 13


class _FixedUtcnow:
    """datetime replacement whose utcnow() returns the fixed BOUND."""

    @classmethod
    def utcnow(cls):
        return BOUND


def _use_db(monkeypatch, db_file):
    """Point the lazy ORM engine/session machinery at db_file."""
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


def _raw_next_review(db_file, concept):
    conn = sqlite3.connect(db_file)
    try:
        row = conn.execute(
            "SELECT next_review FROM tracked_concepts WHERE concept = ?",
            (concept,),
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def test_migration_011_normalizes_t_rows_and_due_query_includes_them(monkeypatch, tmp_path):
    db_file = str(tmp_path / "t_rows.db")
    ensure_base_schema(db_file)

    conn = sqlite3.connect(db_file)
    try:
        conn.executescript(
            """
            INSERT INTO tracked_concepts (concept, first_seen, last_seen, next_review)
            VALUES ('rowA_space', '2026-08-13 06:00:00.000000', '2026-08-13 07:00:00.000000',
                    '2026-08-13 08:00:00.000000');
            INSERT INTO tracked_concepts (concept, first_seen, last_seen, next_review)
            VALUES ('rowB_T', '2026-08-13 06:00:00.000000', '2026-08-13 07:00:00.000000',
                    '2026-08-13T09:00:00');
            INSERT INTO tracked_concepts (concept, first_seen, last_seen, next_review)
            VALUES ('rowC_nextday', '2026-08-13 06:00:00.000000', '2026-08-13 07:00:00.000000',
                    '2026-08-14 08:00:00.000000');
            """
        )
        conn.commit()
    finally:
        conn.close()

    _use_db(monkeypatch, db_file)
    monkeypatch.setattr("tracker_app.learning.concept_scheduler.datetime", _FixedUtcnow)
    try:
        scheduler = ConceptScheduler()

        # Precondition (the FKT-F-004 defect): the same-day 'T' row is excluded
        # from the due query while the space row is due; the future row is not.
        due_before = {d["id"] for d in scheduler.get_due_concepts(limit=50)}
        assert "rowA_space" in due_before
        assert "rowB_T" not in due_before
        assert "rowC_nextday" not in due_before

        # Migration 011 normalizes the stored value (fresh DB: all 12 apply).
        result = run_migrations(db_path=db_file)
        assert result["applied"] == TOTAL_MIGRATIONS
        assert result["failed"] == 0
        assert result["errors"] == []
        assert _raw_next_review(db_file, "rowB_T") == "2026-08-13 09:00:00"
        # LIKE-guarded UPDATE never touches ORM-space rows.
        assert _raw_next_review(db_file, "rowA_space") == "2026-08-13 08:00:00.000000"

        # After normalization the row is due at the boundary it was previously
        # excluded from; the genuinely future row stays excluded.
        due_after = {d["id"] for d in scheduler.get_due_concepts(limit=50)}
        assert "rowA_space" in due_after
        assert "rowB_T" in due_after
        assert "rowC_nextday" not in due_after
    finally:
        _release_engine()


def test_migration_011_noop_when_no_t_rows(monkeypatch, tmp_path):
    db_file = str(tmp_path / "noop.db")
    ensure_base_schema(db_file)

    conn = sqlite3.connect(db_file)
    try:
        conn.execute(
            "INSERT INTO tracked_concepts (concept, first_seen, last_seen, next_review) "
            "VALUES (?,?,?,?)",
            ("space_only", "2026-08-13 06:00:00.000000", "2026-08-13 07:00:00.000000",
             "2026-08-13 08:00:00.000000"),
        )
        conn.commit()
    finally:
        conn.close()

    # First pass on a fresh DB: all 12 migrations apply and 011 has nothing to
    # normalize, so the space row is byte-for-byte unchanged.
    first = run_migrations(db_path=db_file)
    assert first["applied"] == TOTAL_MIGRATIONS
    assert first["failed"] == 0
    assert first["errors"] == []
    assert _raw_next_review(db_file, "space_only") == "2026-08-13 08:00:00.000000"

    # Second pass: everything is recorded, 011 is a no-op, rows unchanged.
    second = run_migrations(db_path=db_file)
    assert second["applied"] == 0
    assert second["skipped"] == TOTAL_MIGRATIONS
    assert second["failed"] == 0
    assert second["errors"] == []
    assert _raw_next_review(db_file, "space_only") == "2026-08-13 08:00:00.000000"

    # The migration itself is recorded in schema_migrations.
    conn = sqlite3.connect(db_file)
    try:
        row = conn.execute(
            "SELECT id FROM schema_migrations WHERE id = '011_datetime_storage_format'"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_populate_writes_space_format_datetimes(tmp_path):
    """populate.py must emit ORM space-format values into every DateTime column.

    Run in a subprocess with FKT_TEST_DB pointing at a throwaway DB: the script
    seeds on import, so executing it in-process would be unsafe (it connects to
    config.DB_PATH). A fresh subprocess reads FKT_TEST_DB before config is
    imported, keeping the real data/sessions.db untouched.
    """
    db_file = str(tmp_path / "populate_seed.db")
    project_root = Path(__file__).resolve().parents[2]

    env = dict(os.environ)
    env["FKT_TEST_DB"] = db_file
    proc = subprocess.run(
        [sys.executable, "-m", "tracker_app.tools.populate"],
        capture_output=True,
        text=True,
        cwd=str(project_root),
        env=env,
    )
    assert proc.returncode == 0, f"populate.py failed:\n{proc.stderr}\n{proc.stdout}"

    date_columns = {
        "sessions": ["start_ts", "end_ts"],
        "multi_modal_logs": ["timestamp"],
        "tracked_concepts": ["first_seen", "last_seen", "next_review"],
        "memory_decay": ["last_seen_ts", "updated_at"],
    }
    conn = sqlite3.connect(db_file)
    try:
        for table, columns in date_columns.items():
            for col in columns:
                rows = conn.execute(f"SELECT {col} FROM {table}").fetchall()
                assert rows, f"{table}.{col} has no seeded rows"
                for (value,) in rows:
                    assert value is not None, f"{table}.{col} contains NULL"
                    assert _SPACE_FORMAT.match(value), (
                        f"{table}.{col} = {value!r} is not space format"
                    )
                    assert value[10] == " ", (
                        f"{table}.{col} = {value!r} has non-space separator at index 10"
                    )
    finally:
        conn.close()
