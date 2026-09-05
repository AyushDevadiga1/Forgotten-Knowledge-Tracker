"""Reset tool for Phase 1 (GIGO remediation).

Purges the synthetic demo rows and near-empty real residue from a target
FKT SQLite database without touching the schema or the 13 migrations.

Safety model (mirrors tools/populate.py):
  * Never targets the default DB implicitly. The target must be stated
    explicitly via --db or the FKT_TEST_DB env var.
  * Without --confirm the tool only prints row counts and refuses to delete.
  * --backup writes a timestamped copy of the DB file before any deletion.
Delete order is child-before-parent so SQLite FK enforcement (migration 006)
never aborts mid-purge.
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime

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


def _existing_tables(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def _row_counts(conn, tables):
    counts = {}
    for table in tables:
        counts[table] = conn.execute('SELECT COUNT(*) FROM "%s"' % table).fetchone()[0]
    return counts


def _migration_count(conn):
    try:
        return conn.execute('SELECT COUNT(*) FROM "schema_migrations"').fetchone()[0]
    except sqlite3.OperationalError:
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Purge demo/residue rows from an FKT SQLite DB (Phase 1).")
    parser.add_argument(
        "--db",
        help="target SQLite file (default: FKT_TEST_DB env var; the default "
        "data/sessions.db is never touched implicitly)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="actually delete rows; without it the tool only reports counts",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="write a timestamped backup copy next to the target before deleting",
    )
    parser.add_argument(
        "--tables",
        default=None,
        help="comma-separated override of the tables to purge (default: all Phase 1 tables)",
    )
    args = parser.parse_args(argv)

    target = args.db or os.environ.get("FKT_TEST_DB")
    if not target:
        print(
            "Reset refused: no target database. Set FKT_TEST_DB or pass --db "
            "(the default DB is never touched implicitly)."
        )
        return 2

    target = os.path.abspath(target)
    if not os.path.exists(target):
        print("Reset no-op: database file not found: %s" % target)
        return 0

    tables = [t.strip() for t in args.tables.split(",") if t.strip()] if args.tables else list(PURGE_TABLES)

    conn = sqlite3.connect(target)
    try:
        existing = _existing_tables(conn)
        present = [t for t in tables if t in existing]
        if not present:
            print("Reset no-op: none of the requested tables exist in %s." % target)
            return 0

        migrations_before = _migration_count(conn)
        before = _row_counts(conn, present)
        total = sum(before.values())
        print("Target    : %s" % target)
        print("Purge plan: %s" % ", ".join(present))
        print("Rows to purge (%d):" % total)
        for table in present:
            print("  %-28s %d" % (table, before[table]))

        if not args.confirm:
            print("Refusing to delete: pass --confirm to proceed.")
            return 1

        if args.backup:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = "%s.backup-%s.db" % (target, stamp)
            dst = sqlite3.connect(backup_path)
            try:
                conn.backup(dst)
            finally:
                dst.close()
            print("Backup written: %s" % backup_path)

        for table in present:
            conn.execute('DELETE FROM "%s"' % table)
        conn.commit()
        after = _row_counts(conn, present)
        remaining = sum(after.values())
        print("Deleted %d rows; %d rows remain in purged tables." % (total, remaining))
        conn.execute("VACUUM")
        migrations_after = _migration_count(conn)
        if migrations_before is not None and migrations_after == migrations_before:
            print("Schema and %d migrations untouched." % migrations_after)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
