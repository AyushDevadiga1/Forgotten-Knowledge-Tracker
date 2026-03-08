# core/db_module.py
import sqlite3
import os
import logging
from contextlib import contextmanager
from tracker_app.config import DB_PATH
from tracker_app.db.models import engine, Base, get_db

logger = logging.getLogger("Database")

@contextmanager
def get_db_connection():
    """Legacy context manager for database connections - mapping everything to single DB_PATH for unified ORM migration"""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")

def ensure_db_directory():
    """Ensure the database directory exists"""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

def init_db():
    ensure_db_directory()
    Base.metadata.create_all(bind=engine)
    logger.info("SQLAlchemy tables constructed: sessions, multi_modal_logs, memory_decay, etc.")

def init_multi_modal_db():
    pass

def init_memory_decay_db():
    pass

def init_metrics_db():
    pass

def init_all_databases():
    """Initialize all database tables using SQLAlchemy ORM"""
    init_db()
    logger.info("All database tables initialized via SQLAlchemy.")

if __name__ == "__main__":
    init_all_databases()