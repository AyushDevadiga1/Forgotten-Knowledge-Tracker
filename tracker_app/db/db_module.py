"""Database initialisation: ensures the DB directory and creates all ORM tables."""

import os
import logging
from tracker_app.config import DB_PATH, get_db_path
from tracker_app.db.models import get_engine, Base
from tracker_app.db.migrations import run_migrations

logger = logging.getLogger("Database")


def ensure_db_directory():
    """Ensure the database directory exists"""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)


def init_db():
    ensure_db_directory()
    Base.metadata.create_all(bind=get_engine())
    logger.info("SQLAlchemy tables constructed: %s", ", ".join(t.name for t in Base.metadata.sorted_tables))


def init_all_databases():
    """Initialize all database tables using SQLAlchemy ORM."""
    init_db()
    # Converge the schema of pre-existing databases: create_all never ALTERs
    # existing tables, so migration-only columns (e.g. intent_predictions.
    # prompted_at/window_title, tracked_concepts.repetitions) would crash the
    # first ORM write with "no such column". run_migrations is idempotent, so
    # calling it here is safe on fresh, current, and stale schemas (FKT-F-002).
    result = run_migrations(db_path=get_db_path())
    logger.info(
        "Migrations at startup: %d applied, %d skipped, %d failed",
        result["applied"],
        result["skipped"],
        result["failed"],
    )
    if result["errors"]:
        logger.error("Migration errors: %s", result["errors"])
    logger.info("All database tables initialized via SQLAlchemy.")


if __name__ == "__main__":
    init_all_databases()
