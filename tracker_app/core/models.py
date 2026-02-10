"""
SQLAlchemy ORM Models for FKT Database

This module defines the database schema using SQLAlchemy ORM,
replacing raw SQL queries for better security and maintainability.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from pathlib import Path

Base = declarative_base()

class LearningItem(Base):
    """Learning items (flashcards) with SM-2 spaced repetition data"""
    __tablename__ = 'learning_items'
    
    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    difficulty = Column(String, default='medium')
    item_type = Column(String, default='concept')
    tags = Column(JSON, default=list)
    interval = Column(Integer, default=1)
    ease_factor = Column(Float, default=2.5)
    repetitions = Column(Integer, default=0)
    next_review_date = Column(DateTime)
    last_review_date = Column(DateTime)
    total_reviews = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    status = Column(String, default='active')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ReviewHistory(Base):
    """History of all review sessions"""
    __tablename__ = 'review_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, nullable=False)
    review_date = Column(DateTime, default=datetime.utcnow)
    quality_rating = Column(Integer, nullable=False)
    correct = Column(Integer, default=0)
    ease_factor = Column(Float)
    interval_days = Column(Integer)
    time_spent_seconds = Column(Float)

class TrackedConcept(Base):
    """Concepts discovered by the automated tracker"""
    __tablename__ = 'tracked_concepts'
    
    id = Column(String, primary_key=True)
    concept = Column(String, nullable=False, unique=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    encounter_count = Column(Integer, default=1)
    relevance_score = Column(Float, default=0.5)
    memory_strength = Column(Float, default=2.5)
    next_review = Column(DateTime)
    context = Column(String)
    related_concepts = Column(JSON, default=list)

class Session(Base):
    """Tracking sessions with intent classification"""
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_ts = Column(DateTime, nullable=False)
    end_ts = Column(DateTime, nullable=False)
    app_name = Column(String)
    window_title = Column(String)
    interaction_rate = Column(Float, default=0)
    interaction_count = Column(Integer, default=0)
    audio_label = Column(String)
    intent_label = Column(String)
    intent_confidence = Column(Float, default=0.0)

# Database connection factory
def get_engine(db_path=None):
    """Create SQLAlchemy engine"""
    if db_path is None:
        from tracker_app.config import DATA_DIR
        db_path = DATA_DIR / "learning_tracker.db"
    
    return create_engine(f'sqlite:///{db_path}', echo=False)

def get_session(engine=None):
    """Get database session"""
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def init_db(engine=None):
    """Initialize all tables"""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database tables initialized with SQLAlchemy ORM")
