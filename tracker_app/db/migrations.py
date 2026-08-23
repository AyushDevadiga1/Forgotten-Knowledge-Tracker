"""SQLite migration runner â€” no Alembic. Applies idempotent MIGRATIONS in order."""

import sqlite3
import logging
import os
from pathlib import Path
from tracker_app.config import DB_PATH


from tracker_app.utils import utcnow as _utcnow

# Table name allowlist for SQL introspection (prevents injection via f-strings)
_KNOWN_TABLES = frozenset(
    {
        "schema_migrations",
        "tracked_concepts",
        "learning_items",
        "review_history",
        "feedback_training_samples",
        "intent_predictions",
        "sessions",
        "multi_modal_logs",
        "memory_decay",
        "metrics",
        "system_sessions",
        "concept_encounters",
    }
)

logger = logging.getLogger("Migrations")


def ensure_base_schema(db_path: str) -> None:
    """Create the ORM-defined base tables before running SQL migrations.

    Migrations 002/004/005 ALTER/INDEX tables that the SQLAlchemy models define
    (tracked_concepts, learning_items, review_history, ...). On a truly fresh
    database (e.g. a clean CI checkout) those tables do not exist yet, so the
    ALTER/INDEX statements would fail with "no such table". Creating the base
    schema first makes `python -m tracker_app.db.migrations` self-sufficient.
    """
    from sqlalchemy import create_engine
    from tracker_app.db.models import Base

    # Path.as_posix() keeps Windows paths portable for sqlite:/// URLs.
    engine = create_engine(f"sqlite:///{Path(db_path).as_posix()}")
    try:
        Base.metadata.create_all(bind=engine)
    finally:
        engine.dispose()


# â”€â”€â”€ Migration registry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Each entry is (migration_id, description, list_of_sql_statements).
# SQL must be idempotent â€” use IF NOT EXISTS / IF EXISTS guards everywhere.
# ADD COLUMN in SQLite cannot be undone, so we only ever add, never drop.

MIGRATIONS = [
    # â”€â”€ 001: Create schema_migrations tracking table itself â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    (
        "001_schema_migrations",
        "Create schema_migrations table",
        [
            """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id          TEXT PRIMARY KEY,
            applied_at  TEXT NOT NULL,
            description TEXT
        )
        """
        ],
    ),
    # â”€â”€ 002: Add AWFC columns to tracked_concepts â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    (
        "002_awfc_columns",
        "Add attention_at_encoding and lambda_personalised to tracked_concepts",
        [
            "ALTER TABLE tracked_concepts ADD COLUMN attention_at_encoding REAL DEFAULT 50.0",
            "ALTER TABLE tracked_concepts ADD COLUMN lambda_personalised   REAL DEFAULT 0.1",
        ],
    ),
    # â”€â”€ 003: Add FeedbackTrainingSample table â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    (
        "003_feedback_table",
        "Create feedback_training_samples table",
        [
            """
        CREATE TABLE IF NOT EXISTS feedback_training_samples (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT    NOT NULL,
            feature_vector  TEXT    NOT NULL,
            predicted_label TEXT    NOT NULL,
            actual_label    TEXT    NOT NULL,
            confidence      REAL    DEFAULT 0.0,
            window_title    TEXT    DEFAULT ''
        )
        """
        ],
    ),
    # â”€â”€ 004: Add indexes on most-queried columns â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    (
        "004_indexes",
        "Add performance indexes",
        [
            "CREATE INDEX IF NOT EXISTS ix_learning_items_next_review_date ON learning_items (next_review_date)",
            "CREATE INDEX IF NOT EXISTS ix_learning_items_status           ON learning_items (status)",
            "CREATE INDEX IF NOT EXISTS ix_review_history_timestamp        ON review_history (timestamp)",
            "CREATE INDEX IF NOT EXISTS ix_tracked_concepts_next_review    ON tracked_concepts (next_review)",
            "CREATE INDEX IF NOT EXISTS ix_tracked_concepts_last_seen      ON tracked_concepts (last_seen)",
            "CREATE INDEX IF NOT EXISTS ix_concept_encounters_timestamp    ON concept_encounters (timestamp)",
            "CREATE INDEX IF NOT EXISTS ix_multi_modal_logs_timestamp      ON multi_modal_logs (timestamp)",
            "CREATE INDEX IF NOT EXISTS ix_feedback_samples_timestamp      ON feedback_training_samples (timestamp)",
        ],
    ),
    # â”€â”€ 005: Add last_review_date column to LearningItem (was missing) â”€â”€â”€â”€â”€â”€â”€
    (
        "005_learning_item_last_review",
        "Add last_review_date to learning_items",
        [
            "ALTER TABLE learning_items ADD COLUMN last_review_date TEXT",
        ],
    ),
    # â”€â”€ 006: Enable WAL mode and FK pragma persistently â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    (
        "006_sqlite_pragmas",
        "Set WAL mode and enable foreign keys",
        [
            "PRAGMA journal_mode=WAL",
            "PRAGMA foreign_keys=ON",
            "PRAGMA synchronous=NORMAL",
        ],
    ),
    # â”€â”€ 007: Feedback-toast rate limiting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    (
        "007_intent_prompted_at",
        "Add prompted_at to intent_predictions",
        [
            "ALTER TABLE intent_predictions ADD COLUMN prompted_at TEXT",
        ],
    ),
    # â”€â”€ 008: Intent feedback retraining data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # context_keywords becomes the JSON 6-feature vector; the window title moves
    # to its own column so it is context, not a substitute for the features.
    (
        "008_intent_window_title",
        "Add window_title to intent_predictions",
        [
            "ALTER TABLE intent_predictions ADD COLUMN window_title TEXT",
        ],
    ),
    # â”€â”€ 009: SM-2 repetition counter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # TrackedConcept previously re-implemented SM-2 by hand off `interval <= 1`,
    # which collapsed the canonical 1-day / 3-day ramp into a straight 3-day
    # jump. A real repetition counter fixes that (Phase 11.6).
    (
        "009_tracked_repetitions",
        "Add repetitions to tracked_concepts",
        [
            "ALTER TABLE tracked_concepts ADD COLUMN repetitions INTEGER DEFAULT 0",
        ],
    ),
    # â”€â”€ 010: Cumulative review counters for lambda recalibration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # recalibrate_lambda() expects a cumulative success rate over n_reviews, but
    # schedule_next_review was passing a single review's quality/5 while also
    # claiming n_reviews = frequency_count (OCR re-encounters, not reviews). The
    # real counters make the success rate a true historical average (M-6).
    (
        "010_tracked_review_counts",
        "Add review_count and correct_count to tracked_concepts",
        [
            "ALTER TABLE tracked_concepts ADD COLUMN review_count  INTEGER DEFAULT 0",
            "ALTER TABLE tracked_concepts ADD COLUMN correct_count INTEGER DEFAULT 0",
        ],
    ),
    # â”€â”€ 011: Normalize raw-writer 'T'-separated datetimes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # populate.py / preflight_check.py used to store datetime.isoformat()
    # values ('2026-08-13T09:00:00') into DateTime columns while the ORM
    # writes and compares space-separated text ('2026-08-13 09:00:00.000000').
    # Because ' ' < 'T' in ASCII, same-day 'T' rows sorted lexicographically
    # AFTER the bound datetime and were silently excluded from due queries
    # until the date flipped (FKT-F-004). These UPDATEs rewrite only text
    # matching the 'T' pattern at position 10, so space-formatted ORM rows and
    # date-only values are never touched, and once normalized no row matches
    # the LIKE guard â€” the migration is idempotent and safe to re-run.
    (
        "011_datetime_storage_format",
        "Normalize 'T'-separated datetimes to ORM space format",
        [
            "UPDATE tracked_concepts SET next_review = substr(next_review,1,10) || ' ' || substr(next_review,12) WHERE next_review LIKE '____-__-__T%'",
            "UPDATE tracked_concepts SET first_seen = substr(first_seen,1,10) || ' ' || substr(first_seen,12) WHERE first_seen LIKE '____-__-__T%'",
            "UPDATE tracked_concepts SET last_seen = substr(last_seen,1,10) || ' ' || substr(last_seen,12) WHERE last_seen LIKE '____-__-__T%'",
            "UPDATE sessions SET start_ts = substr(start_ts,1,10) || ' ' || substr(start_ts,12) WHERE start_ts LIKE '____-__-__T%'",
            "UPDATE sessions SET end_ts = substr(end_ts,1,10) || ' ' || substr(end_ts,12) WHERE end_ts LIKE '____-__-__T%'",
            "UPDATE multi_modal_logs SET timestamp = substr(timestamp,1,10) || ' ' || substr(timestamp,12) WHERE timestamp LIKE '____-__-__T%'",
            "UPDATE memory_decay SET last_seen_ts = substr(last_seen_ts,1,10) || ' ' || substr(last_seen_ts,12) WHERE last_seen_ts LIKE '____-__-__T%'",
            "UPDATE memory_decay SET updated_at = substr(updated_at,1,10) || ' ' || substr(updated_at,12) WHERE updated_at LIKE '____-__-__T%'",
        ],
    ),
    # â”€â”€ 012: Drop duplicate timestamp index on feedback_training_samples â”€â”€â”€â”€â”€â”€
    # Migration 004 created ix_feedback_samples_timestamp, but the ORM model's
    # index=True on FeedbackTrainingSample.timestamp auto-creates
    # ix_feedback_training_samples_timestamp for the same column. Because
    # ensure_base_schema (create_all) runs before migration 004 and the index
    # names differ, IF NOT EXISTS cannot dedupe them â€” migrated databases end
    # up with two indexes on the same column (write amplification on every
    # insert; FKT-F-006). Dropping the legacy migration-004 index converges
    # every path to the single ORM-managed index; IF EXISTS keeps it a no-op
    # on create_all-only databases where the legacy index never existed.
    (
        "012_drop_duplicate_feedback_index",
        "Drop duplicate timestamp index on feedback_training_samples",
        [
            "DROP INDEX IF EXISTS ix_feedback_samples_timestamp",
        ],
    ),
    # ---- 013: Feedback samples consumed by retraining --------------------------------
    # FeedbackTrainingSample rows accumulate forever (F-4). used_in_training marks
    # samples already consumed by a retraining run so a periodic cleanup can delete
    # used rows older than the retention window without losing recent feedback. The
    # ORM column default keeps fresh rows at 0; ADD COLUMN guard makes it a no-op on
    # create_all-only databases.
    (
        "013_feedback_used_in_training",
        "Add used_in_training flag to feedback_training_samples",
        [
            "ALTER TABLE feedback_training_samples ADD COLUMN used_in_training INTEGER DEFAULT 0",
        ],
    ),
]


# â”€â”€â”€ Runner â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def _already_applied(cursor, migration_id: str) -> bool:
    try:
        cursor.execute("SELECT 1 FROM schema_migrations WHERE id = ?", (migration_id,))
        return cursor.fetchone() is not None
    except sqlite3.OperationalError:
        # schema_migrations table doesn't exist yet
        return False


def _mark_applied(cursor, migration_id: str, description: str):
    cursor.execute(
        "INSERT OR IGNORE INTO schema_migrations (id, applied_at, description) VALUES (?, ?, ?)",
        (migration_id, _utcnow().isoformat(), description),
    )


def _column_exists(cursor, table: str, column: str) -> bool:
    if table not in _KNOWN_TABLES:
        raise ValueError(f"Unknown table for introspection: {table!r}")
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _table_exists(cursor, table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def run_migrations(db_path: str = None) -> dict:
    """
    Run all pending migrations against the FKT SQLite database.

    Returns:
        {'applied': int, 'skipped': int, 'failed': int, 'errors': list}
    """
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ensure_base_schema(path)

    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    cursor = conn.cursor()

    applied = skipped = failed = 0
    errors = []

    for migration_id, description, statements in MIGRATIONS:
        if _already_applied(cursor, migration_id):
            skipped += 1
            logger.debug(f"  [SKIP] {migration_id}")
            continue

        logger.info(f"  [APPLY] {migration_id}: {description}")
        migration_ok = True

        for sql in statements:
            sql = sql.strip()
            if not sql:
                continue

            # Guard ALTER TABLE ADD COLUMN â€” SQLite errors if column already exists
            if "ADD COLUMN" in sql.upper():
                parts = sql.split()
                try:
                    col_idx = parts.index("COLUMN") + 1
                    col_name = parts[col_idx]
                    tbl_idx = parts.index("TABLE") + 1
                    tbl_name = parts[tbl_idx]
                    if _column_exists(cursor, tbl_name, col_name):
                        logger.debug(f"    Column {tbl_name}.{col_name} already exists â€” skipping")
                        continue
                except (ValueError, IndexError):
                    pass

            try:
                cursor.execute(sql)
                conn.commit()
            except sqlite3.OperationalError as e:
                err_msg = str(e)
                # Tolerate "duplicate column" and "already exists" as non-fatal
                if "already exists" in err_msg or "duplicate column" in err_msg:
                    logger.debug(f"    Tolerated: {err_msg}")
                else:
                    logger.error(f"    FAILED: {err_msg}")
                    logger.error(f"    SQL: {sql[:120]}")
                    errors.append(f"{migration_id}: {err_msg}")
                    migration_ok = False
                    break

        if migration_ok:
            _mark_applied(cursor, migration_id, description)
            conn.commit()
            applied += 1
            logger.info(f"  [OK]   {migration_id}")
        else:
            failed += 1

    conn.close()
    return {"applied": applied, "skipped": skipped, "failed": failed, "errors": errors}


def print_status(db_path: str = None):
    """Print current migration status."""
    path = db_path or DB_PATH
    if not os.path.exists(path):
        print(f"Database not found at {path}")
        return

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    all_ids = [m[0] for m in MIGRATIONS]
    applied_ids = set()

    if _table_exists(cursor, "schema_migrations"):
        cursor.execute("SELECT id FROM schema_migrations")
        applied_ids = {row[0] for row in cursor.fetchall()}

    conn.close()

    print(f"\nMigration status - {path}")
    print(f"{'-' * 55}")
    for mid in all_ids:
        status = "[OK]    applied" if mid in applied_ids else "[--]    pending"
        print(f"  {status}  {mid}")
    print(f"{'-' * 55}")
    pending = len(all_ids) - len(applied_ids & set(all_ids))
    print(f"  {len(applied_ids & set(all_ids))} applied, {pending} pending\n")


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    if "--status" in sys.argv:
        print_status()
    else:
        print("Running FKT database migrations...")
        result = run_migrations()
        print(f"\nDone: {result['applied']} applied, {result['skipped']} skipped, {result['failed']} failed")
        if result["errors"]:
            print("Errors:")
            for e in result["errors"]:
                print(f"  x {e}")
            sys.exit(1)
        else:
            print("All migrations successful.")
