"""SQLAlchemy ORM models for all FKT tables (lazy engine/session factories)."""

from tracker_app.utils import utcnow as _utcnow

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, event, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
import logging

from tracker_app.config import get_db_path


Base = declarative_base()

# â”€â”€â”€ Lazy engine factory â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Creating the engine at module import time means FKT_TEST_DB env overrides
# only work if they are set BEFORE the first import of this module â€” fragile
# in test setups that configure the env programmatically.
#
# The lazy pattern below defers creation until first use, so tests can safely
# set FKT_TEST_DB at the top of a test file and get the correct DB path.

_engine = None
_SessionLocal = None


def get_engine():
    """Return the shared SQLAlchemy engine, creating it on first call."""
    global _engine
    if _engine is None:
        # Re-read the DB path at call time: get_db_path() queries the
        # environment fresh, so FKT_TEST_DB set after this module was
        # imported still selects the right database. (config.DB_PATH is
        # frozen at import time and would be a no-op here.)
        _engine = create_engine(
            f"sqlite:///{get_db_path()}",
            connect_args={"check_same_thread": False},
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return _engine


def get_session_local():
    """Return the shared sessionmaker, creating it on first call."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


# â”€â”€â”€ Backward-compatible module-level aliases â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Existing code that does `from tracker_app.db.models import SessionLocal`
# continues to work: accessing the attribute calls through to the lazy getter.


class _LazySessionProxy:
    """Proxy that forwards all calls to the lazily-created SessionLocal."""

    def __call__(self, *args, **kwargs):
        # Re-resolve the current module attribute: module-scope importers
        # (e.g. `from tracker_app.db.models import SessionLocal`) capture this
        # proxy, so if models.SessionLocal was rebound afterwards (tests
        # patching models.SessionLocal), delegate to the rebound object
        # instead of silently forwarding to the global _SessionLocal.
        import tracker_app.db.models as models_mod

        current = getattr(models_mod, "SessionLocal", self)
        if current is not self:
            return current(*args, **kwargs)
        return get_session_local()(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(get_session_local(), name)


SessionLocal = _LazySessionProxy()


# engine at module level is kept for code that accesses it directly
# (e.g. Base.metadata.create_all(bind=engine) in db_module.py).
# It resolves lazily via the property-like function below.
class _LazyEngineProxy:
    def __getattr__(self, name):
        # Re-resolve the current module attribute: a proxy captured at import
        # time (e.g. `from tracker_app.db.models import engine`) must honor a
        # later rebinding of models.engine instead of always resolving the
        # default get_engine().
        import tracker_app.db.models as models_mod

        current = getattr(models_mod, "engine", self)
        if current is not self:
            return getattr(current, name)
        return getattr(get_engine(), name)

    def __repr__(self):
        return repr(get_engine())


engine = _LazyEngineProxy()


def get_db():
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


# â”€â”€â”€ Active Model Logging â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Listens for all SQLAlchemy flush events and logs exactly what records
# were inserted, updated, or deleted. This satisfies the requirement to
# "log each of the changes and all and it is saved as logs".

db_logger = logging.getLogger("DB_Models")


@event.listens_for(Session, "after_flush")
def receive_after_flush(session, flush_context):
    for obj in session.new:
        db_logger.info(f"INSERTED [{obj.__class__.__name__}]: {obj.__dict__}")
    for obj in session.dirty:
        db_logger.info(f"UPDATED  [{obj.__class__.__name__}]: {obj.__dict__}")
    for obj in session.deleted:
        db_logger.info(f"DELETED  [{obj.__class__.__name__}]: {obj.__dict__}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Learning Tracker Models
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class LearningItem(Base):
    __tablename__ = "learning_items"

    id = Column(String, primary_key=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    difficulty = Column(String, default="medium")
    item_type = Column(String, default="concept")
    tags = Column(String, default="")

    # SM-2 scheduling
    interval = Column(Integer, default=0)
    ease_factor = Column(Float, default=2.5)
    repetitions = Column(Integer, default=0)
    next_review_date = Column(DateTime, index=True)  # â† DateTime + index
    last_review_date = Column(DateTime, nullable=True)  # â† maps migration 005 column

    # Stats
    total_reviews = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    status = Column(String, default="active", index=True)  # â† index

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationship
    reviews = relationship("ReviewHistory", back_populates="item", cascade="all, delete-orphan", passive_deletes=True)


class ReviewHistory(Base):
    __tablename__ = "review_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, ForeignKey("learning_items.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=_utcnow, nullable=False, index=True)
    quality_rating = Column(Integer)
    old_interval = Column(Integer)
    new_interval = Column(Integer)
    old_ease = Column(Float)
    new_ease = Column(Float)

    item = relationship("LearningItem", back_populates="reviews")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Intent & Activity Models
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class IntentPrediction(Base):
    __tablename__ = "intent_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=_utcnow, nullable=False, index=True)
    predicted_intent = Column(String)
    confidence = Column(Float)
    context_keywords = Column(String)  # JSON: [f1, f2, f3, f4, f5, f6] feature vector
    user_feedback = Column(Integer, nullable=True)  # 1=correct 0=wrong
    actual_intent = Column(String, nullable=True)
    feedback_timestamp = Column(DateTime, nullable=True)
    prompted_at = Column(DateTime, nullable=True)  # when the feedback toast last surfaced this row
    window_title = Column(String, nullable=True)  # what was on screen when predicted


class IntentAccuracy(Base):
    __tablename__ = "intent_accuracy"

    intent = Column(String, primary_key=True)
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=_utcnow)


class TrackingSession(Base):
    __tablename__ = "tracking_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime)
    duration_minutes = Column(Float)
    concepts_encountered = Column(Integer)
    avg_attention = Column(Float)
    primary_activity = Column(String)


class DailySummary(Base):
    __tablename__ = "daily_summary"

    # date kept as String (YYYY-MM-DD key, not a full timestamp)
    date = Column(String, primary_key=True)
    total_tracking_minutes = Column(Float)
    concepts_encountered = Column(Integer)
    avg_attention = Column(Float)
    primary_intents = Column(String)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Concept Tracking Models
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class TrackedConcept(Base):
    __tablename__ = "tracked_concepts"

    concept = Column(String, primary_key=True)
    first_seen = Column(DateTime, default=_utcnow, nullable=False)
    last_seen = Column(DateTime, default=_utcnow, nullable=False, index=True)
    frequency_count = Column(Integer, default=1)
    relevance_score = Column(Float, default=0.5)
    context_tags = Column(String, default="")
    status = Column(String, default="discovered")

    # SM-2 scheduling fields
    interval = Column(Integer, default=1)
    memory_strength = Column(Float, default=2.5)
    next_review = Column(DateTime, index=True)  # â† DateTime + index (critical query path)
    repetitions = Column(Integer, default=0)  # consecutive successful reviews
    review_count = Column(Integer, default=0)  # total quiz reviews (recalibration denominator)
    correct_count = Column(Integer, default=0)  # total correct quiz reviews

    # AWFC fields â€” attention at time of first learning
    # NULL means no attention was measured at capture time (no AWFC
    # personalisation); a real measurement replaces it on first encounter.
    attention_at_encoding = Column(Float)
    lambda_personalised = Column(Float, default=0.1)  # personalised decay rate

    # Relationship
    encounters = relationship(
        "ConceptEncounter", back_populates="tracked_concept", cascade="all, delete-orphan", passive_deletes=True
    )


class ConceptEncounter(Base):
    __tablename__ = "concept_encounters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    concept = Column(String, ForeignKey("tracked_concepts.concept", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=_utcnow, nullable=False, index=True)
    source = Column(String)  # 'ocr' | 'browser_extension' | 'manual'
    confidence = Column(Float, default=1.0)
    context_snippet = Column(String)

    tracked_concept = relationship("TrackedConcept", back_populates="encounters")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# System Session Models
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class SystemSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_ts = Column(DateTime, index=True)
    end_ts = Column(DateTime)
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
    timestamp = Column(DateTime, nullable=False, index=True)
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
    keyword = Column(String, nullable=False, index=True)
    last_seen_ts = Column(DateTime, nullable=False, index=True)
    predicted_recall = Column(Float, default=0.0)
    observed_usage = Column(Integer, default=1)
    updated_at = Column(DateTime, default=_utcnow)


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    concept = Column(String)
    next_review_time = Column(DateTime)
    memory_score = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=_utcnow)


# â”€â”€â”€ Self-improving model: feedback training samples â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class FeedbackTrainingSample(Base):
    """
    Stores user-corrected intent predictions for model retraining.
    Populated when a user clicks 'wrong' on an IntentFeedbackToast.
    Used by scripts/train_models_from_logs.py --include-feedback.
    """

    __tablename__ = "feedback_training_samples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=_utcnow, nullable=False, index=True)
    feature_vector = Column(String, nullable=False)  # JSON: [f1, f2, f3, f4, f5, f6]
    predicted_label = Column(String, nullable=False)
    actual_label = Column(String, nullable=False)  # ground truth from user
    confidence = Column(Float, default=0.0)
    window_title = Column(String, default="")
    used_in_training = Column(Integer, default=0, nullable=False)


# --- C3: DB-backed session toggle state ---


class SessionToggle(Base):
    """Stores the start/stop toggle state. Single row (id=1)."""

    __tablename__ = "session_toggle"

    id = Column(Integer, primary_key=True, default=1)
    active = Column(Boolean, default=False, nullable=False)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class EarCalibration(Base):
    """Stores the latest EAR calibration data. Single row (id=1)."""

    __tablename__ = "ear_calibration"

    id = Column(Integer, primary_key=True, default=1)
    personal_ear_low = Column(Float, nullable=True)
    personal_ear_high = Column(Float, nullable=True)
    mean_ear = Column(Float, nullable=True)
    std_ear = Column(Float, nullable=True)
    fallback = Column(Boolean, default=False)
    raw_data = Column(String, nullable=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


# --- H3: Concept promotion triage queue ---


class TriageQueue(Base):
    __tablename__ = "triage_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    concept = Column(String, nullable=False, unique=True, index=True)
    answer = Column(String, default="")
    difficulty = Column(String, default="medium")
    status = Column(String, default="pending")  # pending, approved, rejected
    frequency_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)
    reviewed_at = Column(DateTime, nullable=True)
