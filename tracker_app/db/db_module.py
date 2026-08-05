"""Database initialisation: ensures the DB directory and creates all ORM tables."""
import os
import logging
from tracker_app.config import DB_PATH
from tracker_app.db.models import get_engine, Base, get_db

logger = logging.getLogger("Database")

def ensure_db_directory():
    """Ensure the database directory exists"""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

def init_db():
    ensure_db_directory()
    Base.metadata.create_all(bind=get_engine())
    logger.info("SQLAlchemy tables constructed: sessions, multi_modal_logs, memory_decay, etc.")

def init_all_databases():
    """Initialize all database tables using SQLAlchemy ORM"""
    init_db()
    logger.info("All database tables initialized via SQLAlchemy.")

if __name__ == "__main__":
    init_all_databases()