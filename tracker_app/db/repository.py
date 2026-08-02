"""
Data Access Object (DAO) / Repository Layer
Abstracts SQLAlchemy models and query logic away from the business layer.
"""
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from tracker_app.db.models import (
    LearningItem, 
    ReviewHistory,
    TrackingSession,
    IntentPrediction,
    IntentAccuracy,
    FeedbackTrainingSample
)

class LearningRepository:
    """Repository for CRUD operations on learning items and their reviews."""
    
    @staticmethod
    def get_item(db: Session, item_id: str) -> Optional[LearningItem]:
        return db.query(LearningItem).filter(LearningItem.id == item_id).first()

    @staticmethod
    def get_items_due(db: Session, limit: int = 20) -> List[LearningItem]:
        return db.query(LearningItem)\
                 .filter(LearningItem.status == 'active')\
                 .filter(LearningItem.next_review_date <= datetime.now())\
                 .order_by(LearningItem.next_review_date.asc())\
                 .limit(limit)\
                 .all()

    @staticmethod
    def get_all_items(db: Session) -> List[LearningItem]:
        return db.query(LearningItem).all()
        
    @staticmethod
    def get_total_count(db: Session) -> int:
        return db.query(LearningItem).count()
        
    @staticmethod
    def add_item(db: Session, item: LearningItem) -> None:
        db.add(item)
        db.commit()
        db.refresh(item)
        
    @staticmethod
    def delete_item(db: Session, item_id: str) -> bool:
        item = db.query(LearningItem).filter(LearningItem.id == item_id).first()
        if item:
            db.delete(item)
            db.commit()
            return True
        return False

    @staticmethod
    def record_review(db: Session, review: ReviewHistory, item: LearningItem) -> None:
        db.add(review)
        # SQLAlchemy implicitly tracks changes to `item` attached to the session
        db.commit()
        db.refresh(item)
        
    @staticmethod
    def get_stats(db: Session) -> Dict[str, Any]:
        now = datetime.now()
        total_active = db.query(LearningItem).filter(LearningItem.status == 'active').count()
        total_due = db.query(LearningItem)\
                      .filter(LearningItem.status == 'active')\
                      .filter(LearningItem.next_review_date <= now)\
                      .count()
        
        mastered = db.query(LearningItem).filter(LearningItem.status == 'mastered').count()
        
        return {
            "total_active": total_active,
            "total_due": total_due,
            "mastered": mastered
        }
        
    @staticmethod
    def get_learning_today(db: Session) -> Dict[str, Any]:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now()
        reviews_today = db.query(ReviewHistory).filter(
            ReviewHistory.timestamp >= today_start,
            ReviewHistory.timestamp <= today_end
        ).all()
        
        total_reviews = len(reviews_today)
        correct_reviews = sum(1 for r in reviews_today if r.quality_rating >= 3)
        return {
            'reviews_today': total_reviews,
            'correct_today': correct_reviews,
            'accuracy_today': (correct_reviews / total_reviews * 100) if total_reviews else 0
        }

    @staticmethod
    def search_items(db: Session, query: str) -> List[LearningItem]:
        from sqlalchemy import or_
        search_term = f"%{query}%"
        return db.query(LearningItem).filter(
            LearningItem.status == "active",
            or_(
                LearningItem.question.like(search_term),
                LearningItem.answer.like(search_term)
            )
        ).order_by(LearningItem.created_at.desc()).all()

    @staticmethod
    def get_items(db: Session, status: str = 'active', limit: int = 50) -> List[LearningItem]:
        q = db.query(LearningItem)
        if status != 'all':
            q = q.filter(LearningItem.status == status)
        return q.order_by(LearningItem.created_at.desc()).limit(limit).all()


class TrackingRepository:
    """Repository for session tracking and intent prediction telemetrics."""
    
    @staticmethod
    def log_session(db: Session, session_data: TrackingSession) -> None:
        db.add(session_data)
        db.commit()
        
    @staticmethod
    def log_intent_prediction(db: Session, prediction: IntentPrediction) -> None:
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        
    @staticmethod
    def get_intent_prediction(db: Session, prediction_id: int) -> Optional[IntentPrediction]:
        return db.query(IntentPrediction).filter(IntentPrediction.id == prediction_id).first()

    @staticmethod
    def get_recent_intent_prediction(db: Session) -> Optional[IntentPrediction]:
        return db.query(IntentPrediction).order_by(IntentPrediction.timestamp.desc()).first()
        
    @staticmethod
    def update_intent_accuracy(db: Session, intent_label: str, is_correct: bool) -> None:
        acc = db.query(IntentAccuracy).filter(IntentAccuracy.intent == intent_label).first()
        if not acc:
            acc = IntentAccuracy(
                intent=intent_label,
                total_predictions=0,
                correct_predictions=0,
                accuracy=0.0
            )
            db.add(acc)
            
        acc.total_predictions += 1
        if is_correct:
            acc.correct_predictions += 1
            
        acc.accuracy = acc.correct_predictions / acc.total_predictions
        acc.last_updated = datetime.now()
        db.commit()

    @staticmethod
    def get_accuracy_stats(db: Session) -> Dict[str, Any]:
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
        
    @staticmethod
    def get_daily_summary(db: Session, date: Optional[datetime] = None) -> Dict[str, Any]:
        if date is None:
            date = datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        
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
        
    @staticmethod
    def get_trend_analysis(db: Session, days: int = 7) -> Dict[str, Any]:
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
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

class FeedbackRepository:
    """Repository for machine learning feedback and retraining data."""
    
    @staticmethod
    def log_feedback_sample(db: Session, sample: FeedbackTrainingSample) -> None:
        db.add(sample)
        db.commit()
        
    @staticmethod
    def get_all_samples(db: Session) -> List[FeedbackTrainingSample]:
        return db.query(FeedbackTrainingSample).all()

    @staticmethod
    def get_total_count(db: Session) -> int:
        return db.query(FeedbackTrainingSample).count()
