import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from tracker_app.config import DATA_DIR, DB_PATH

# Rather than managing 5 different DBs, we unify them into one standard DB for SQLAlchemy
# Or we can respect DB_PATH if we want to migrate seamlessly.
# For now, let's use the DB_PATH from config (default: sessions.db) as the unified DB.
engine = create_engine(
    f"sqlite:///{DB_PATH}", 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables defined in models."""
    Base.metadata.create_all(bind=engine)
