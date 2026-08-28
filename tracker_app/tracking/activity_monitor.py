import os
import json
from collections import deque
from datetime import datetime
from threading import Lock
from typing import Dict, Any, Optional
import logging

from tracker_app.utils import utcnow as _utcnow

from tracker_app.config import DATA_DIR
from tracker_app.constants import CONTEXT_MAX_LENGTH, NEUTRAL_ATTENTION
from tracker_app.learning.concept_scheduler import ConceptScheduler
from tracker_app.db.repository import TrackingRepository
from tracker_app.db.models import SessionLocal, IntentPrediction, TrackingSession, MultiModalLog


logger = logging.getLogger("ActivityMonitor")


class ThreadSafeCounter:
    """Thread-safe counter for keyboard and mouse events"""

    def __init__(self):
        self._value = 0
        self._lock = Lock()

    def increment(self):
        with self._lock:
            self._value += 1

    def get_and_reset(self):
        with self._lock:
            value = self._value
            self._value = 0
            return value


class IntentValidator:
    """Validates and improves intent predictions over time.

    Writes directly to the shared ORM database (sessions.db) so that
    the web API reads the same data the tracker writes.
    """

    def __init__(self, db_path: str = None):
        # db_path parameter kept for backward-compat but ignored; all writes
        # now go through the shared SQLAlchemy engine in models.py.
        self.prediction_buffer = deque(maxlen=100)

    def log_prediction(self, predicted_intent: str, confidence: float, context: str = "", features=None):
        """Log an intent prediction to the shared ORM database.

        context is the active window title (kept for display context).
        features is the exact 6-element feature vector the classifier saw â€”
        JSON-encoded into context_keywords so feedback-driven retraining
        (ADR-003) gets real inputs, not a window-title string.
        """
        try:
            with SessionLocal() as db:
                pred = IntentPrediction(
                    timestamp=_utcnow(),
                    predicted_intent=predicted_intent,
                    confidence=confidence,
                    context_keywords=json.dumps(features) if features else "[]",
                    window_title=context or "",
                )
                TrackingRepository.log_intent_prediction(db, pred)
        except Exception as e:
            logger.error(f"Failed to log intent prediction: {e}")

        self.prediction_buffer.append({"intent": predicted_intent, "confidence": confidence, "timestamp": _utcnow()})

    def get_accuracy_stats(self) -> Dict[str, Any]:
        """Get overall intent prediction accuracy"""
        try:
            with SessionLocal() as db:
                return TrackingRepository.get_accuracy_stats(db)
        except Exception as e:
            logger.error(f"Failed to get accuracy stats: {e}")
            return {"average_accuracy": 0.5, "intents_tracked": 0, "best_accuracy": 0, "worst_accuracy": 0}


class TrackingAnalytics:
    """Analytics on tracked concepts and sessions.

    Writes directly to the shared ORM database (sessions.db) so that
    the web API reads the same data the tracker writes.
    """

    def __init__(self, db_path: str = None):
        # db_path parameter kept for backward-compat; all writes go through ORM.
        pass

    def log_session(
        self, start_time: datetime, end_time: datetime, concepts_count: int, avg_attention: float, primary_activity: str
    ):
        """Log a tracking session to the shared ORM database"""
        try:
            with SessionLocal() as db:
                duration = (end_time - start_time).total_seconds() / 60
                session = TrackingSession(
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=duration,
                    concepts_encountered=concepts_count,
                    avg_attention=avg_attention,
                    primary_activity=primary_activity,
                )
                TrackingRepository.log_session(db, session)
        except Exception as e:
            logger.error(f"Failed to log tracking session: {e}")

    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get daily tracking summary"""
        try:
            with SessionLocal() as db:
                return TrackingRepository.get_daily_summary(db, date)
        except Exception as e:
            logger.error(f"Failed to get daily summary: {e}")
            date_str = date.strftime("%Y-%m-%d") if date else _utcnow().strftime("%Y-%m-%d")
            return {"date": date_str, "total_minutes": 0, "concepts": 0, "avg_attention": 0}

    def get_trend_analysis(self, days: int = 7) -> Dict[str, Any]:
        """Analyze tracking trends"""
        try:
            with SessionLocal() as db:
                return TrackingRepository.get_trend_analysis(db, days)
        except Exception as e:
            logger.error(f"Failed to get trend analysis: {e}")
            return {
                "tracking_days": 0,
                "avg_session_minutes": 0,
                "total_concepts_encountered": 0,
                "avg_attention_score": 0,
            }


class ActivityMonitor:
    """Main enhanced tracker combining all improvements (formerly EnhancedActivityTracker)"""

    def __init__(self):
        self.scheduler = ConceptScheduler()
        self.validator = IntentValidator()
        self.analytics = TrackingAnalytics()

        self.keyboard_counter = ThreadSafeCounter()
        self.mouse_counter = ThreadSafeCounter()

        self.session_start = None
        self.session_concepts = []
        self._attention_sum = 0.0
        self._attention_count = 0

        # State tracking
        self.is_running = False
        self._lock = Lock()

    def start_session(self):
        """Start a tracking session"""
        with self._lock:
            self.session_start = _utcnow()
            self.session_concepts = []
            self._attention_sum = 0.0
            self._attention_count = 0
            self.is_running = True
        logger.info(f"Tracking session started at {self.session_start}")

    def end_session(self):
        """End tracking session and save analytics"""
        with self._lock:
            if not self.is_running:
                return

            session_end = _utcnow()

            # Calculate session stats
            concepts_count = len(set(self.session_concepts))
            avg_attention = self._attention_sum / self._attention_count if self._attention_count else 0

            # Determine primary activity
            primary_activity = "general_browsing"
            if self.session_concepts:
                from collections import Counter

                activity_counts = Counter(self.session_concepts)
                primary_activity = activity_counts.most_common(1)[0][0]

            # Log to analytics
            self.analytics.log_session(self.session_start, session_end, concepts_count, avg_attention, primary_activity)

            # Metrics must come from real sessions: persist one Metric row per
            # distinct session concept with its live AWFC memory score (D5).
            self._persist_session_metrics()

            self.is_running = False
            # Log inside the lock while variables are guaranteed to be defined
            logger.info(f"Tracking session ended. Concepts: {concepts_count}, Avg Attention: {avg_attention:.2f}")

    def process_concepts(
        self,
        ocr_keywords: Dict[str, Any],
        confidence: float = 0.6,
        attention_score: float = 50.0,
        context_text: str = "",
    ):
        """Process and schedule encountered concepts.
        Passes attention_score to concept_scheduler for AWFC Î» personalisation.
        """
        for concept, info in ocr_keywords.items():
            if not concept or len(concept) < 2:
                continue
            try:
                concept_conf = float(info.get("score", confidence) if isinstance(info, dict) else confidence)
                saved = self.scheduler.add_concept(
                    concept,
                    concept_conf,
                    # Real sanitized capture text, never the literal 'ocr'
                    # token (capture fidelity). Sensitive/redacted windows
                    # left context_text empty, so nothing is persisted.
                    context=context_text[:CONTEXT_MAX_LENGTH],
                    attention_at_encoding=attention_score,  # AWFC
                )
                if saved:
                    self.session_concepts.append(concept)
            except Exception as e:
                logger.error(f"Error processing concept {concept}: {e}")

    def process_intent(self, intent_result: Dict[str, Any], context: str = ""):
        """Process intent prediction with validation.
        context is the window title; intent_result['features'] is the exact
        feature vector used at prediction time (stored for retraining).
        """
        intent = intent_result.get("intent_label", "unknown")
        confidence = intent_result.get("confidence", 0.5)

        # Log for validation â€” persists the real feature vector, not the title
        self.validator.log_prediction(
            intent,
            confidence,
            context=context,
            features=intent_result.get("features"),
        )

    def update_attention(self, attention_score: float):
        """Track attention/focus levels"""
        self._attention_sum += attention_score
        self._attention_count += 1

    def log_multimodal(
        self,
        window_title: str = "",
        keywords: Optional[Dict[str, Any]] = None,
        audio_label: str = "silence",
        attention_score: float = NEUTRAL_ATTENTION,
        interaction_rate: float = 0.0,
        intent_label: str = "unknown",
        intent_confidence: float = 0.0,
    ):
        """Persist one multi-modal log row for a capture cycle (D5).

        memory_score is derived from the knowledge graph's live score for the
        window's concepts where available, so telemetry carries real retention
        data instead of a constant placeholder.
        """
        try:
            memory_score = self._avg_window_memory(keywords)
            with SessionLocal() as db:
                log_row = MultiModalLog(
                    timestamp=_utcnow(),
                    window_title=window_title,
                    ocr_keywords=json.dumps(keywords or {}),
                    audio_label=audio_label,
                    attention_score=attention_score,
                    interaction_rate=interaction_rate,
                    intent_label=intent_label,
                    intent_confidence=intent_confidence,
                    memory_score=memory_score,
                )
                TrackingRepository.log_multimodal(db, log_row)
        except Exception as e:
            logger.error(f"Failed to log multimodal data: {e}")

    def _avg_window_memory(self, keywords: Optional[Dict[str, Any]]) -> float:
        """Average graph memory_score for the window's concepts (0.0 when none)."""
        if not keywords:
            return 0.0
        try:
            from tracker_app.tracking.knowledge_graph import knowledge_graph as _kg

            scores = [
                _kg.nodes[k].get("memory_score", 0.0)
                for k in keywords
                if k in _kg and isinstance(_kg.nodes[k].get("memory_score"), (int, float))
            ]
            return round(sum(scores) / len(scores), 4) if scores else 0.0
        except Exception:
            return 0.0

    def _persist_session_metrics(self):
        """Write one Metric row per distinct concept captured this session."""
        concepts = set(self.session_concepts)
        if not concepts:
            return
        try:
            from tracker_app.config import DEFAULT_LAMBDA
            from tracker_app.db.models import Metric, TrackedConcept
            from tracker_app.learning.memory_model import compute_memory_score_awfc
        except Exception:
            return
        for concept in concepts:
            try:
                with SessionLocal() as db:
                    row = db.query(TrackedConcept).filter(TrackedConcept.concept == concept).first()
                    if row is None:
                        continue
                    score = compute_memory_score_awfc(
                        row.last_seen or row.first_seen,
                        base_lambda=row.lambda_personalised or DEFAULT_LAMBDA,
                        attention_at_encoding=row.attention_at_encoding or 50.0,
                    )
                    db.add(
                        Metric(
                            concept=concept,
                            next_review_time=row.next_review,
                            memory_score=round(score, 4),
                            last_updated=_utcnow(),
                        )
                    )
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to persist metric for {concept}: {e}")

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        with self._lock:
            if not self.is_running or not self.session_start:
                return {}

            elapsed = (_utcnow() - self.session_start).total_seconds() / 60

            return {
                "session_duration_minutes": elapsed,
                "concepts_encountered": len(set(self.session_concepts)),
                "avg_attention": self._attention_sum / self._attention_count if self._attention_count else 0,
                "is_active": self.is_running,
            }

    def export_tracking_data(self, output_file: str = None):
        """Export all tracking data to DATA_DIR (or a provided absolute path)."""
        if output_file is None:
            output_file = str(DATA_DIR / "tracking_export.json")

        due_concepts = self.scheduler.get_due_concepts(1000)
        intent_stats = self.validator.get_accuracy_stats()
        daily_stats = self.analytics.get_daily_summary()
        trend_stats = self.analytics.get_trend_analysis(30)

        export_data = {
            "timestamp": _utcnow().isoformat(),
            "session_stats": self.get_session_stats(),
            "due_concepts": due_concepts,
            "intent_accuracy": intent_stats,
            "daily_summary": daily_stats,
            "trend_analysis": trend_stats,
        }

        parent = os.path.dirname(output_file)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Tracking data exported to {output_file}")
        return export_data
