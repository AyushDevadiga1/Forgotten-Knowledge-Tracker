import time
import os
import sqlite3
import json
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import logging

from tracker_app.config import DATA_DIR
from tracker_app.learning.concept_scheduler import ConceptScheduler

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
    
    def get_value(self):
        with self._lock:
            return self._value


class IntentValidator:
    """Validates and improves intent predictions over time.
    
    Writes directly to the shared ORM database (sessions.db) so that
    the web API reads the same data the tracker writes.
    """
    
    def __init__(self, db_path: str = None):
        # db_path parameter kept for backward-compat but ignored; all writes
        # now go through the shared SQLAlchemy engine in models.py.
        self.prediction_buffer = []
    
    def log_prediction(self, predicted_intent: str, confidence: float, context: str):
        """Log an intent prediction to the shared ORM database"""
        try:
            from tracker_app.db.models import SessionLocal, IntentPrediction
            with SessionLocal() as db:
                pred = IntentPrediction(
                    timestamp=datetime.now().isoformat(),
                    predicted_intent=predicted_intent,
                    confidence=confidence,
                    context_keywords=context
                )
                db.add(pred)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to log intent prediction: {e}")
        
        self.prediction_buffer.append({
            'intent': predicted_intent,
            'confidence': confidence,
            'timestamp': datetime.now()
        })
    
    def log_feedback(self, prediction_id: int, correct: bool):
        """User provides feedback on prediction accuracy"""
        try:
            from tracker_app.db.models import SessionLocal, IntentPrediction, IntentAccuracy
            with SessionLocal() as db:
                pred = db.query(IntentPrediction).filter(IntentPrediction.id == prediction_id).first()
                if pred:
                    pred.user_feedback = 1 if correct else 0
                    pred.feedback_timestamp = datetime.now().isoformat()
                    intent = pred.predicted_intent
                    
                    # Update accuracy stats
                    acc = db.query(IntentAccuracy).filter(IntentAccuracy.intent == intent).first()
                    if acc is None:
                        acc = IntentAccuracy(
                            intent=intent,
                            total_predictions=1,
                            correct_predictions=1 if correct else 0,
                        )
                        db.add(acc)
                    else:
                        acc.total_predictions += 1
                        if correct:
                            acc.correct_predictions += 1
                        acc.accuracy = acc.correct_predictions / acc.total_predictions
                        acc.last_updated = datetime.now().isoformat()
                    
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to log intent feedback: {e}")
    
    def get_accuracy_stats(self) -> Dict[str, Any]:
        """Get overall intent prediction accuracy"""
        try:
            from tracker_app.db.models import SessionLocal, IntentAccuracy
            with SessionLocal() as db:
                from sqlalchemy import func
                row = db.query(
                    func.avg(IntentAccuracy.accuracy),
                    func.count(IntentAccuracy.intent),
                    func.max(IntentAccuracy.accuracy),
                    func.min(IntentAccuracy.accuracy)
                ).filter(IntentAccuracy.total_predictions >= 5).first()
                
                return {
                    'average_accuracy': row[0] or 0.5,
                    'intents_tracked': row[1] or 0,
                    'best_accuracy': row[2] or 0,
                    'worst_accuracy': row[3] or 0
                }
        except Exception as e:
            logger.error(f"Failed to get accuracy stats: {e}")
            return {'average_accuracy': 0.5, 'intents_tracked': 0, 'best_accuracy': 0, 'worst_accuracy': 0}


class TrackingAnalytics:
    """Analytics on tracked concepts and sessions.
    
    Writes directly to the shared ORM database (sessions.db) so that
    the web API reads the same data the tracker writes.
    """
    
    def __init__(self, db_path: str = None):
        # db_path parameter kept for backward-compat; all writes go through ORM.
        pass
    
    def log_session(self, start_time: datetime, end_time: datetime, 
                   concepts_count: int, avg_attention: float, primary_activity: str):
        """Log a tracking session to the shared ORM database"""
        try:
            from tracker_app.db.models import SessionLocal, TrackingSession
            with SessionLocal() as db:
                duration = (end_time - start_time).total_seconds() / 60
                session = TrackingSession(
                    start_time=start_time.isoformat(),
                    end_time=end_time.isoformat(),
                    duration_minutes=duration,
                    concepts_encountered=concepts_count,
                    avg_attention=avg_attention,
                    primary_activity=primary_activity
                )
                db.add(session)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to log tracking session: {e}")
    
    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get daily tracking summary"""
        if date is None:
            date = datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        
        try:
            from tracker_app.db.models import SessionLocal, TrackingSession
            from sqlalchemy import func
            with SessionLocal() as db:
                row = db.query(
                    func.sum(TrackingSession.duration_minutes),
                    func.sum(TrackingSession.concepts_encountered),
                    func.avg(TrackingSession.avg_attention)
                ).filter(
                    TrackingSession.start_time.like(f"{date_str}%")
                ).first()
                
                return {
                    'date': date_str,
                    'total_minutes': row[0] or 0,
                    'concepts': row[1] or 0,
                    'avg_attention': row[2] or 0
                }
        except Exception as e:
            logger.error(f"Failed to get daily summary: {e}")
            return {'date': date_str, 'total_minutes': 0, 'concepts': 0, 'avg_attention': 0}
    
    def get_trend_analysis(self, days: int = 7) -> Dict[str, Any]:
        """Analyze tracking trends"""
        try:
            from tracker_app.db.models import SessionLocal, TrackingSession
            from sqlalchemy import func
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with SessionLocal() as db:
                row = db.query(
                    func.count(TrackingSession.id),
                    func.avg(TrackingSession.duration_minutes),
                    func.sum(TrackingSession.concepts_encountered),
                    func.avg(TrackingSession.avg_attention)
                ).filter(
                    TrackingSession.start_time >= start_date
                ).first()
                
                return {
                    'tracking_days': row[0] or 0,
                    'avg_session_minutes': row[1] or 0,
                    'total_concepts_encountered': row[2] or 0,
                    'avg_attention_score': row[3] or 0
                }
        except Exception as e:
            logger.error(f"Failed to get trend analysis: {e}")
            return {'tracking_days': 0, 'avg_session_minutes': 0, 'total_concepts_encountered': 0, 'avg_attention_score': 0}


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
        self.session_attention_scores = []
        
        # State tracking
        self.is_running = False
        self._lock = Lock()
    
    def start_session(self):
        """Start a tracking session"""
        with self._lock:
            self.session_start = datetime.now()
            self.session_concepts = []
            self.session_attention_scores = []
            self.is_running = True
        logger.info(f"Tracking session started at {self.session_start}")
    
    def end_session(self):
        """End tracking session and save analytics"""
        with self._lock:
            if not self.is_running:
                return
            
            session_end = datetime.now()
            
            # Calculate session stats
            concepts_count = len(set(self.session_concepts))
            avg_attention = sum(self.session_attention_scores) / len(self.session_attention_scores) if self.session_attention_scores else 0
            
            # Determine primary activity
            primary_activity = "general_browsing"
            if self.session_concepts:
                from collections import Counter
                activity_counts = Counter(self.session_concepts)
                primary_activity = activity_counts.most_common(1)[0][0]
            
            # Log to analytics
            self.analytics.log_session(
                self.session_start,
                session_end,
                concepts_count,
                avg_attention,
                primary_activity
            )
            
            self.is_running = False
            # Log inside the lock while variables are guaranteed to be defined
            logger.info(f"Tracking session ended. Concepts: {concepts_count}, Avg Attention: {avg_attention:.2f}")
    
    def process_concepts(
        self,
        ocr_keywords: Dict[str, Any],
        confidence: float = 0.6,
        attention_score: float = 50.0,
    ):
        """Process and schedule encountered concepts.
        Passes attention_score to concept_scheduler for AWFC λ personalisation.
        """
        for concept, info in ocr_keywords.items():
            if not concept or len(concept) < 2:
                continue
            try:
                concept_conf = float(
                    info.get('score', confidence)
                    if isinstance(info, dict) else confidence
                )
                self.scheduler.add_concept(
                    concept,
                    concept_conf,
                    context="ocr",
                    attention_at_encoding=attention_score,  # AWFC
                )
                self.session_concepts.append(concept)
            except Exception as e:
                logger.error(f"Error processing concept {concept}: {e}")
    
    def process_intent(self, intent_result: Dict[str, Any], context: str = ""):
        """Process intent prediction with validation"""
        intent = intent_result.get('intent_label', 'unknown')
        confidence = intent_result.get('confidence', 0.5)
        
        # Log for validation
        self.validator.log_prediction(intent, confidence, context)
    
    def update_attention(self, attention_score: float):
        """Track attention/focus levels"""
        self.session_attention_scores.append(attention_score)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        with self._lock:
            if not self.is_running or not self.session_start:
                return {}
            
            elapsed = (datetime.now() - self.session_start).total_seconds() / 60
            
            return {
                'session_duration_minutes': elapsed,
                'concepts_encountered': len(set(self.session_concepts)),
                'avg_attention': sum(self.session_attention_scores) / len(self.session_attention_scores) if self.session_attention_scores else 0,
                'is_active': self.is_running
            }
    
    def get_concept_recommendations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top concepts to review"""
        return self.scheduler.get_due_concepts(limit)
    
    def export_tracking_data(self, output_file: str = "data/tracking_export.json"):
        """Export all tracking data"""
        due_concepts = self.scheduler.get_due_concepts(1000)
        intent_stats = self.validator.get_accuracy_stats()
        daily_stats = self.analytics.get_daily_summary()
        trend_stats = self.analytics.get_trend_analysis(30)
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'session_stats': self.get_session_stats(),
            'due_concepts': due_concepts,
            'intent_accuracy': intent_stats,
            'daily_summary': daily_stats,
            'trend_analysis': trend_stats
        }
        
        os.makedirs(os.path.dirname(output_file) or "data", exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Tracking data exported to {output_file}")
        return export_data
