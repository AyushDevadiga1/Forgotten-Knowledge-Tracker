"""
Data Access Object (DAO) / Repository Layer
Abstracts SQLAlchemy models and query logic away from the business layer.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from tracker_app.utils import utcnow as _utcnow
from tracker_app.constants import MASTERY_MIN_REPETITIONS, MASTERY_SUCCESS_RATE

from tracker_app.db.models import (
    LearningItem,
    ReviewHistory,
    TrackingSession,
    IntentPrediction,
    IntentAccuracy,
    FeedbackTrainingSample,
    TrackedConcept,
)


class LearningRepository:
    """Repository for CRUD operations on learning items and their reviews."""

    @staticmethod
    def get_item(db: Session, item_id: str) -> Optional[LearningItem]:
        return db.query(LearningItem).filter(LearningItem.id == item_id).first()

    @staticmethod
    def get_items_due(db: Session, limit: int = 20) -> List[LearningItem]:
        return (
            db.query(LearningItem)
            .filter(LearningItem.status == "active")
            .filter(LearningItem.next_review_date <= _utcnow())
            .order_by(LearningItem.next_review_date.asc())
            .limit(limit)
            .all()
        )

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
    def record_review(db: Session, review: ReviewHistory, item: LearningItem) -> None:
        db.add(review)
        # SQLAlchemy implicitly tracks changes to `item` attached to the session
        db.commit()
        db.refresh(item)

    @staticmethod
    def get_stats(db: Session) -> Dict[str, Any]:
        now = _utcnow()
        total_active = db.query(LearningItem).filter(LearningItem.status == "active").count()
        total_due = (
            db.query(LearningItem)
            .filter(LearningItem.status == "active")
            .filter(LearningItem.next_review_date <= now)
            .count()
        )

        mastered = db.query(LearningItem).filter(LearningItem.status == "mastered").count()

        return {"total_active": total_active, "total_due": total_due, "mastered": mastered}

    @staticmethod
    def get_learning_today(db: Session) -> Dict[str, Any]:
        today_start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = _utcnow()
        reviews_today = (
            db.query(ReviewHistory)
            .filter(ReviewHistory.timestamp >= today_start, ReviewHistory.timestamp <= today_end)
            .all()
        )

        total_reviews = len(reviews_today)
        correct_reviews = sum(1 for r in reviews_today if r.quality_rating >= 3)
        concepts_studied = db.query(TrackedConcept).filter(TrackedConcept.last_seen >= today_start).count()
        return {
            "reviews_today": total_reviews,
            "correct_today": correct_reviews,
            "accuracy_today": (correct_reviews / total_reviews * 100) if total_reviews else 0,
            "concepts_studied": concepts_studied,
        }

    @staticmethod
    def get_review_trend(db: Session, days: int = 7) -> List[Dict[str, Any]]:
        """Real per-day time-series over the last N days (oldest â†’ newest).

        Every figure is derived from stored timestamps â€” reviews/correctness
        from `review_history`, items added from `learning_items.created_at`,
        mastery from the first review where the stored mastery rule holds, and
        due items from `next_review_date`. Nothing is simulated.
        """
        from datetime import timedelta

        today = _utcnow().date()
        dates = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
        by_day = {
            d: {"date": d.isoformat(), "reviews": 0, "correct": 0, "added": 0, "mastered": 0, "due": 0} for d in dates
        }

        reviews = db.query(ReviewHistory.timestamp, ReviewHistory.quality_rating).all()
        for ts, quality in reviews:
            if ts is None:
                continue
            day = ts.date()
            if day in by_day:
                by_day[day]["reviews"] += 1
                if quality is not None and quality >= 3:
                    by_day[day]["correct"] += 1

        items = db.query(
            LearningItem.id,
            LearningItem.created_at,
            LearningItem.status,
            LearningItem.next_review_date,
        ).all()
        for _item_id, created, status, next_review in items:
            if created is not None and created.date() in by_day:
                by_day[created.date()]["added"] += 1
            if status == "active" and next_review is not None and next_review.date() in by_day:
                by_day[next_review.date()]["due"] += 1

        for item_id, created, status, _next in items:
            if status != "mastered":
                continue
            item_reviews = (
                db.query(ReviewHistory.timestamp, ReviewHistory.quality_rating)
                .filter(ReviewHistory.item_id == item_id)
                .order_by(ReviewHistory.timestamp.asc())
                .all()
            )
            if not item_reviews:
                day = created.date() if created is not None else None
            else:
                total = correct = 0
                day = None
                for ts, quality in item_reviews:
                    if ts is None:
                        continue
                    total += 1
                    if quality is not None and quality >= 3:
                        correct += 1
                    if total > MASTERY_MIN_REPETITIONS and (correct / total) > MASTERY_SUCCESS_RATE:
                        day = ts.date()
                        break
                if day is None:
                    day = item_reviews[-1][0].date()
            if day is not None and day in by_day:
                by_day[day]["mastered"] += 1

        out = list(by_day.values())
        for entry in out:
            entry["accuracy"] = round(entry["correct"] / entry["reviews"] * 100) if entry["reviews"] else 0
        return out

    @staticmethod
    def search_items(db: Session, query: str) -> List[LearningItem]:
        from sqlalchemy import or_

        search_term = f"%{query}%"
        return (
            db.query(LearningItem)
            .filter(
                LearningItem.status == "active",
                or_(LearningItem.question.like(search_term), LearningItem.answer.like(search_term)),
            )
            .order_by(LearningItem.created_at.desc())
            .all()
        )

    @staticmethod
    def get_items(db: Session, status: str = "active", limit: int = 50) -> List[LearningItem]:
        q = db.query(LearningItem)
        if status != "all":
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
            acc = IntentAccuracy(intent=intent_label, total_predictions=0, correct_predictions=0, accuracy=0.0)
            db.add(acc)

        acc.total_predictions += 1
        if is_correct:
            acc.correct_predictions += 1

        acc.accuracy = acc.correct_predictions / acc.total_predictions
        acc.last_updated = _utcnow()
        db.commit()

    @staticmethod
    def get_accuracy_stats(db: Session) -> Dict[str, Any]:
        row = (
            db.query(
                func.avg(IntentAccuracy.accuracy),
                func.count(IntentAccuracy.intent),
                func.max(IntentAccuracy.accuracy),
                func.min(IntentAccuracy.accuracy),
            )
            .filter(IntentAccuracy.total_predictions >= 5)
            .first()
        )

        return {
            "average_accuracy": row[0] or 0.5,
            "intents_tracked": row[1] or 0,
            "best_accuracy": row[2] or 0,
            "worst_accuracy": row[3] or 0,
        }

    @staticmethod
    def get_daily_summary(db: Session, date: Optional[datetime] = None) -> Dict[str, Any]:
        from datetime import timedelta

        if date is None:
            date = _utcnow()
        date_str = date.strftime("%Y-%m-%d")
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        next_day = day_start + timedelta(days=1)

        row = (
            db.query(
                func.sum(TrackingSession.duration_minutes),
                func.sum(TrackingSession.concepts_encountered),
                func.avg(TrackingSession.avg_attention),
            )
            .filter(TrackingSession.start_time >= day_start, TrackingSession.start_time < next_day)
            .first()
        )

        return {"date": date_str, "total_minutes": row[0] or 0, "concepts": row[1] or 0, "avg_attention": row[2] or 0}

    @staticmethod
    def get_trend_analysis(db: Session, days: int = 7) -> Dict[str, Any]:
        from datetime import timedelta

        # Bind the datetime OBJECT, not a string: SQLite stores DateTime as
        # "YYYY-MM-DD HH:MM:SS" while isoformat() uses "T", so a string compare
        # lexicographically mis-excludes every session on the boundary day that
        # started after the cutoff time-of-day (space < 'T').
        start_date = _utcnow() - timedelta(days=days)

        row = (
            db.query(
                func.count(TrackingSession.id),
                func.avg(TrackingSession.duration_minutes),
                func.sum(TrackingSession.concepts_encountered),
                func.avg(TrackingSession.avg_attention),
            )
            .filter(TrackingSession.start_time >= start_date)
            .first()
        )

        return {
            "tracking_days": row[0] or 0,
            "avg_session_minutes": row[1] or 0,
            "total_concepts_encountered": row[2] or 0,
            "avg_attention_score": row[3] or 0,
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

    @staticmethod
    def mark_samples_used(db: Session, sample_ids) -> None:
        """Mark feedback samples as consumed by a retraining run (F-4)."""
        if not sample_ids:
            return
        db.query(FeedbackTrainingSample).filter(FeedbackTrainingSample.id.in_(sample_ids)).update(
            {FeedbackTrainingSample.used_in_training: 1},
            synchronize_session=False,
        )
        db.commit()

    @staticmethod
    def cleanup_used_samples(db: Session, older_than: datetime) -> int:
        """Delete used training samples older than `older_than`. Returns the
        number of rows deleted (F-4)."""
        deleted = (
            db.query(FeedbackTrainingSample)
            .filter(
                FeedbackTrainingSample.used_in_training == 1,
                FeedbackTrainingSample.timestamp < older_than,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted
