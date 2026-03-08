import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from tracker_app.config import DB_PATH

Base = declarative_base()

# Unified Database Engine
engine = create_engine(
    f"sqlite:///{DB_PATH}", 
    connect_args={"check_same_thread": False},
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# Learning Tracker Models
# ==========================================
class LearningItem(Base):
    __tablename__ = "learning_items"
    
    id = Column(String, primary_key=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    difficulty = Column(String, default="medium")
    item_type = Column(String, default="concept")
    tags = Column(String, default="")
    
    # SM-2 fields
    interval = Column(Integer, default=0)
    ease_factor = Column(Float, default=2.5)
    repetitions = Column(Integer, default=0)
    next_review_date = Column(String)
    
    # Stats
    total_reviews = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    status = Column(String, default="active")
    
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat())

class ReviewHistory(Base):
    __tablename__ = "review_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, index=True)
    timestamp = Column(String, default=lambda: datetime.now().isoformat())
    quality_rating = Column(Integer)
    old_interval = Column(Integer)
    new_interval = Column(Integer)
    old_ease = Column(Float)
    new_ease = Column(Float)

# ==========================================
# Intent & Activity Models
# ==========================================
class IntentPrediction(Base):
    __tablename__ = "intent_predictions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String, default=lambda: datetime.now().isoformat(), index=True)
    predicted_intent = Column(String)
    confidence = Column(Float)
    context_keywords = Column(String)
    user_feedback = Column(Integer, nullable=True) # 1 or 0
    actual_intent = Column(String, nullable=True)
    feedback_timestamp = Column(String, nullable=True)

class IntentAccuracy(Base):
    __tablename__ = "intent_accuracy"
    
    intent = Column(String, primary_key=True)
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    last_updated = Column(String, default=lambda: datetime.now().isoformat())

class TrackingSession(Base):
    __tablename__ = "tracking_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(String)
    end_time = Column(String)
    duration_minutes = Column(Float)
    concepts_encountered = Column(Integer)
    avg_attention = Column(Float)
    primary_activity = Column(String)

class DailySummary(Base):
    __tablename__ = "daily_summary"
    
    date = Column(String, primary_key=True)
    total_tracking_minutes = Column(Float)
    concepts_encountered = Column(Integer)
    avg_attention = Column(Float)
    primary_intents = Column(String)

# ==========================================
# Concept Tracking Models
# ==========================================
class TrackedConcept(Base):
    __tablename__ = "tracked_concepts"
    
    concept = Column(String, primary_key=True)
    first_seen = Column(String, default=lambda: datetime.now().isoformat())
    last_seen = Column(String, default=lambda: datetime.now().isoformat())
    frequency_count = Column(Integer, default=1)
    relevance_score = Column(Float, default=0.5)
    context_tags = Column(String, default="")
    status = Column(String, default="discovered")
    
    # SM2 scheduling logic
    interval = Column(Integer, default=1)
    memory_strength = Column(Float, default=2.5)
    next_review = Column(String)

class ConceptEncounter(Base):
    __tablename__ = "concept_encounters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    concept = Column(String, index=True)
    timestamp = Column(String, default=lambda: datetime.now().isoformat())
    source = Column(String)
    confidence = Column(Float, default=1.0)
    context_snippet = Column(String)

# ==========================================
# System Sessions Models
# ==========================================
class SystemSession(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_ts = Column(String, index=True)
    end_ts = Column(String)
    app_name = Column(String)
    window_title = Column(String)
    interaction_rate = Column(Float, default=0)
    interaction_count = Column(Integer, default=0)
    audio_label = Column(String)
    intent_label = Column(String)
    intent_confidence = Column(Float, default=0.0)

class MultiModalLog(Base):
    __tablename__ = "multi_modal_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String, index=True)
    window_title = Column(String)
    ocr_keywords = Column(String)
    audio_label = Column(String)
    attention_score = Column(Float, default=0)
    interaction_rate = Column(Float, default=0)
    intent_label = Column(String)
    intent_confidence = Column(Float, default=0.0)
    memory_score = Column(Float, default=0.0)

class MemoryDecay(Base):
    __tablename__ = "memory_decay"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String, index=True)
    last_seen_ts = Column(String, index=True)
    predicted_recall = Column(Float, default=0.0)
    observed_usage = Column(Integer, default=1)
    updated_at = Column(String)

class Metric(Base):
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    concept = Column(String)
    next_review_time = Column(String)
    memory_score = Column(Float, default=0.0)
    last_updated = Column(String)
