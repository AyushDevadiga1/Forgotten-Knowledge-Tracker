"""Reset guard (GIGO Phase 1): reset_database.py must never purge without an
explicit target and --confirm, and must leave the schema + migrations intact."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PURGE_TABLES = [
    "review_history",
    "learning_items",
    "concept_encounters",
    "intent_predictions",
    "intent_accuracy",
    "feedback_training_samples",
    "triage_queue",
    "multi_modal_logs",
    "memory_decay",
    "metrics",
    "sessions",
    "tracked_concepts",
]


def _run_reset(db_file, *args):
    env = dict(os.environ)
    env["FKT_TEST_DB"] = str(db_file)
    env["SECRET_KEY"] = "test-secret"
    return subprocess.run(
        [sys.executable, "-m", "tracker_app.tools.reset_database", *args],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=env,
    )


def _run_reset_without_target(*args):
    env = dict(os.environ)
    env["FKT_TEST_DB"] = ""
    env["SECRET_KEY"] = "test-secret"
    return subprocess.run(
        [sys.executable, "-m", "tracker_app.tools.reset_database", *args],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=env,
    )


def _make_seeded_db(db_file):
    """Create schema via the real init path, then insert rows that mirror the
    demo-seed shape (including a parent/child FK pair)."""
    env = dict(os.environ)
    env["FKT_TEST_DB"] = str(db_file)
    env["SECRET_KEY"] = "test-secret"
    subprocess.run(
        [sys.executable, "-c", "from tracker_app.db.db_module import init_all_databases; init_all_databases()"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=env,
        check=True,
    )
    conn = sqlite3.connect(str(db_file))
    try:
        conn.executescript(
            """
            INSERT INTO tracked_concepts (concept, first_seen, last_seen)
                VALUES ('alpha', '2026-01-01T00:00:00', '2026-01-01T00:00:00');
            INSERT INTO concept_encounters (concept, timestamp, source, confidence, context_snippet)
                VALUES ('alpha', '2026-01-01T00:00:00', 'browser_extension', 1.0, 'real snippet');
            INSERT INTO sessions (start_ts, end_ts, app_name, window_title)
                VALUES ('2026-01-01T00:00:00', '2026-01-01T01:00:00', 'Chrome', 'quicksort');
            INSERT INTO metrics (concept, memory_score, last_updated)
                VALUES ('__seed__', 0.0, '2026-01-01T00:00:00');
            """
        )
        conn.commit()
    finally:
        conn.close()


def _counts(db_file, tables):
    conn = sqlite3.connect(str(db_file))
    try:
        return {t: conn.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0] for t in tables}
    finally:
        conn.close()


def test_reset_without_explicit_target_refuses(tmp_path):
    db_file = tmp_path / "never_created.db"
    proc = _run_reset_without_target()
    assert proc.returncode == 2
    assert "Reset refused" in proc.stdout
    assert "FKT_TEST_DB" in proc.stdout
    assert not Path(db_file).exists()


def test_reset_missing_file_is_clean_noop(tmp_path):
    db_file = tmp_path / "never_created.db"
    proc = _run_reset(db_file)
    assert proc.returncode == 0
    assert "no-op" in proc.stdout
    assert not Path(db_file).exists()


def test_reset_without_confirm_refuses_and_preserves_rows(tmp_path):
    db_file = tmp_path / "seeded.db"
    _make_seeded_db(db_file)
    proc = _run_reset(db_file)
    assert proc.returncode == 1
    assert "Refusing to delete" in proc.stdout
    assert "Rows to purge" in proc.stdout
    before = _counts(db_file, PURGE_TABLES)
    assert before["tracked_concepts"] == 1
    assert before["concept_encounters"] == 1
    assert before["sessions"] == 1


def test_reset_confirm_purges_rows_and_keeps_schema(tmp_path):
    db_file = tmp_path / "seeded.db"
    _make_seeded_db(db_file)
    migrations_before = _counts(db_file, ["schema_migrations"])["schema_migrations"]
    proc = _run_reset(db_file, "--confirm")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    after = _counts(db_file, PURGE_TABLES)
    assert all(v == 0 for v in after.values())
    tables = [r[0] for r in sqlite3.connect(str(db_file)).execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for table in PURGE_TABLES:
        assert table in tables, "table must survive a row purge"
    assert _counts(db_file, ["schema_migrations"])["schema_migrations"] == migrations_before
    assert "migrations untouched" in proc.stdout


def test_reset_backup_writes_timestamped_copy(tmp_path):
    db_file = tmp_path / "seeded.db"
    _make_seeded_db(db_file)
    proc = _run_reset(db_file, "--confirm", "--backup")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    backups = sorted(tmp_path.glob("seeded.db.backup-*.db"))
    assert len(backups) == 1
    assert _counts(backups[0], ["tracked_concepts"])["tracked_concepts"] == 1


def test_reset_tables_override_purges_only_selected(tmp_path):
    db_file = tmp_path / "seeded.db"
    _make_seeded_db(db_file)
    proc = _run_reset(db_file, "--confirm", "--tables", "metrics")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    counts = _counts(db_file, PURGE_TABLES)
    assert counts["metrics"] == 0
    assert counts["tracked_concepts"] == 1
    assert counts["sessions"] == 1
