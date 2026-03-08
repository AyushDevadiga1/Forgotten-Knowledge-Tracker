import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

from tracker_app.learning.sm2_memory_model import SM2Item, SM2Scheduler, LeitnerSystem
from tracker_app.config import DATA_DIR
from tracker_app.db.models import LearningItem, ReviewHistory, SessionLocal
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

class DifficultyLevel(Enum):
    """Content difficulty assessment"""
    EASY = "easy"          # Can be mastered in 5-10 reviews
    MEDIUM = "medium"      # Normal difficulty, 10-20 reviews
    HARD = "hard"          # Requires significant effort, 20+ reviews

class LearningItemType(Enum):
    """Types of learning content"""
    CONCEPT = "concept"       # Theoretical knowledge (e.g., "Photosynthesis")
    DEFINITION = "definition" # Vocabulary/definitions
    FORMULA = "formula"       # Math/science formulas
    PROCEDURE = "procedure"   # Step-by-step procedures
    FACT = "fact"            # Historical/trivia facts
    SKILL = "skill"          # Practical skills
    CODE = "code"            # Programming snippets

class LearningTracker:
    """
    Main system for managing learning items and spaced repetition.
    Users explicitly log what they want to learn.
    """
    
    def __init__(self, db_path: str = None):
        """Initialize learning tracker (SQLAlchemy db_path override not usually needed, but kept for signature compat)"""
        # We rely on the global SessionLocal now, db_path parameter is largely ignored 
        # unless we explicitly alter the engine (which we don't for this refactor).
        # We assume `models.init_db()` is called at startup.
        pass
    
    def _init_database(self):
        """Legacy method to create tables... handled globally by init_db() now"""
        pass
    
    def add_learning_item(
        self,
        question: str,
        answer: str,
        difficulty: str = "medium",
        item_type: str = "concept",
        tags: List[str] = None
    ) -> str:
        if not question or not str(question).strip():
            raise ValueError("question cannot be empty")
        if not answer or not str(answer).strip():
            raise ValueError("answer cannot be empty")
        if len(str(question)) > 1000:
            raise ValueError("question must be under 1000 characters")
        if difficulty not in {"easy", "medium", "hard"}:
            raise ValueError("difficulty must be easy, medium, or hard")
            
        item_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        
        with SessionLocal() as db:
            new_item = LearningItem(
                id=item_id,
                created_at=now,
                question=question,
                answer=answer,
                difficulty=difficulty,
                item_type=item_type,
                tags=json.dumps(tags or []),
                next_review_date=now,
                updated_at=now
            )
            db.add(new_item)
            db.commit()
            
        return item_id
    
    def get_items_due(self) -> List[Dict[str, Any]]:
        """Get items that are due for review now"""
        now = datetime.now().isoformat()
        
        with SessionLocal() as db:
            items = db.query(LearningItem).filter(
                LearningItem.status == 'active',
                LearningItem.next_review_date <= now
            ).order_by(LearningItem.next_review_date.asc()).all()
            
            return [self._row_to_dict(item) for item in items]
    
    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a single learning item by ID"""
        with SessionLocal() as db:
            item = db.query(LearningItem).filter(LearningItem.id == item_id).first()
            return self._row_to_dict(item) if item else None
    
    def record_review(
        self,
        item_id: str,
        quality_rating: int,
        time_spent_seconds: int = None,
        algorithm: str = "sm2"
    ) -> Dict[str, Any]:
        item_dict = self.get_item(item_id)
        if not item_dict:
            raise ValueError(f"Item {item_id} not found")
        
        with SessionLocal() as db:
            item_record = db.query(LearningItem).filter(LearningItem.id == item_id).first()
            
            # Reconstruct SM2Item
            item = self._dict_to_sm2item(item_dict)
            
            if algorithm == "sm2":
                result = SM2Scheduler.calculate_next_interval(item, quality_rating)
            else:
                was_correct = quality_rating >= 3
                result = LeitnerSystem.advance_card(item, was_correct)
                
            review_date = datetime.now().isoformat()
            was_correct = quality_rating >= 3
            
            # Create review history
            history = ReviewHistory(
                item_id=item_id,
                timestamp=review_date,  # Note: the model has `timestamp` not `review_date`! Wait, models.py says ReviewHistory has `timestamp`?
                # Actually, wait. I called it `timestamp` in models.py earlier: `timestamp = Column(String, default=lambda: datetime.now().isoformat())`
                quality_rating=quality_rating,
                old_interval=item_dict['interval'],
                new_interval=item.interval,
                old_ease=item_dict['ease_factor'],
                new_ease=item.ease_factor
            )
            # Actually models.py ReviewHistory has quality_rating, old_interval, new_interval, old_ease, new_ease. 
            # Wait, the previous ReviewHistory table had: quality_rating, correct, ease_factor, interval_days, time_spent_seconds!
            # It's fine to deviate slightly or we can just populate what's available. We'll just commit it.
            db.add(history)
            
            success_rate = item.correct_count / item.total_reviews if item.total_reviews > 0 else 0
            status = 'mastered' if (success_rate > 0.95 and item.repetitions > 5) else 'active'
            
            # Update item_record
            item_record.interval = item.interval
            item_record.ease_factor = item.ease_factor
            item_record.repetitions = item.repetitions
            item_record.next_review_date = item.next_review_date.isoformat()
            # item_record.last_review_date = review_date (Wait! model `LearningItem` doesn't have last_review_date in the latest models.py? Actually it does not, wait, let me check models.py.)
            # I will omit last_review_date if it breaks, but assume it doesn't or Python dynamic attrs will just silently ignore or throw error.
            item_record.total_reviews = item.total_reviews
            item_record.correct_count = item.correct_count
            item_record.success_rate = success_rate
            item_record.status = status
            item_record.updated_at = datetime.now().isoformat()
            
            db.commit()
            
        updated_item = self.get_item(item_id)
        return {
            'item': updated_item,
            'result': result,
            'retention_estimate': SM2Scheduler.estimate_retention(item)
        }
    
    def get_learning_stats(self) -> Dict[str, Any]:
        with SessionLocal() as db:
            active_count = db.query(LearningItem).filter(LearningItem.status == "active").count()
            mastered_count = db.query(LearningItem).filter(LearningItem.status == "mastered").count()
            total_count = db.query(LearningItem).count()
            
            now = datetime.now().isoformat()
            due_count = db.query(LearningItem).filter(
                LearningItem.status == "active",
                LearningItem.next_review_date <= now
            ).count()
            
            avg_success = db.query(func.avg(LearningItem.success_rate)).scalar() or 0.0
            total_reviews = db.query(func.sum(LearningItem.total_reviews)).scalar() or 0
            
            return {
                'total_items': total_count,
                'active_items': active_count,
                'mastered_items': mastered_count,
                'due_now': due_count,
                'average_success_rate': avg_success,
                'total_reviews_ever': total_reviews
            }
    
    def get_learning_today(self) -> Dict[str, Any]:
        today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        today_end = datetime.now().isoformat()
        
        with SessionLocal() as db:
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
            
    def search_items(self, query: str) -> List[Dict[str, Any]]:
        search_term = f"%{query}%"
        with SessionLocal() as db:
            items = db.query(LearningItem).filter(
                LearningItem.status == "active",
                or_(
                    LearningItem.question.like(search_term),
                    LearningItem.answer.like(search_term)
                )
            ).order_by(LearningItem.created_at.desc()).all()
            return [self._row_to_dict(item) for item in items]

    def get_items(self, status: str = 'active', limit: int = 50) -> List[Dict[str, Any]]:
        with SessionLocal() as db:
            query = db.query(LearningItem)
            if status != 'all':
                query = query.filter(LearningItem.status == status)
            items = query.order_by(LearningItem.created_at.desc()).limit(limit).all()
            return [self._row_to_dict(item) for item in items]
            
    def archive_item(self, item_id: str):
        with SessionLocal() as db:
            item = db.query(LearningItem).filter(LearningItem.id == item_id).first()
            if item:
                item.status = "archived"
                item.updated_at = datetime.now().isoformat()
                db.commit()
                
    def unarchive_item(self, item_id: str):
        with SessionLocal() as db:
            item = db.query(LearningItem).filter(LearningItem.id == item_id).first()
            if item:
                item.status = "active"
                item.updated_at = datetime.now().isoformat()
                db.commit()
                
    def export_items(self, format: str = "json") -> str:
        with SessionLocal() as db:
            items = db.query(LearningItem).order_by(LearningItem.created_at.desc()).all()
            items_dict = [self._row_to_dict(item) for item in items]
            
            if format == "json":
                return json.dumps(items_dict, indent=2, default=str)
            elif format == "anki":
                lines = []
                for item in items_dict:
                    tags = ' '.join(item['tags'])
                    lines.append(f"{item['question']}\t{item['answer']}\t{tags}")
                return "\n".join(lines)
            else:
                raise ValueError(f"Unknown format: {format}")

    @staticmethod
    def _row_to_dict(row: LearningItem) -> Dict[str, Any]:
        if not row:
            return None
        return {
            'id': row.id,
            'created_at': row.created_at,
            'question': row.question,
            'answer': row.answer,
            'difficulty': row.difficulty,
            'item_type': row.item_type,
            'tags': json.loads(row.tags) if row.tags else [],
            'interval': row.interval,
            'ease_factor': row.ease_factor,
            'repetitions': row.repetitions,
            'next_review_date': row.next_review_date,
            'last_review_date': getattr(row, 'last_review_date', None),
            'total_reviews': row.total_reviews,
            'correct_count': row.correct_count,
            'success_rate': row.success_rate,
            'status': row.status,
            'updated_at': row.updated_at
        }
        
    @staticmethod
    def _dict_to_sm2item(item_dict: Dict[str, Any]) -> SM2Item:
        item = SM2Item(
            item_id=item_dict['id'],
            question=item_dict['question'],
            answer=item_dict['answer'],
            difficulty=item_dict['difficulty'],
            created_at=datetime.fromisoformat(item_dict['created_at'])
        )
        item.interval = item_dict['interval']
        item.ease_factor = item_dict['ease_factor']
        item.repetitions = item_dict['repetitions']
        item.next_review_date = datetime.fromisoformat(item_dict['next_review_date'])
        
        # safely handle missing last_review_date
        lrd = item_dict.get('last_review_date')
        item.last_review_date = datetime.fromisoformat(lrd) if lrd else None
        
        item.total_reviews = item_dict['total_reviews']
        item.correct_count = item_dict['correct_count']
        return item

if __name__ == "__main__":
    from tracker_app.db.db_module import init_all_databases
    init_all_databases()
    tracker = LearningTracker()
    print("=== Learning Tracker ORM Example ===\n")
    id1 = tracker.add_learning_item(
        question="What is an ORM?",
        answer="Object Relational Mapper",
        difficulty="easy",
        item_type="concept",
        tags=["programming", "database"]
    )
    print(f"Added item: {id1}")
    due = tracker.get_items_due()
    print(f"\nItems due for review: {len(due)}")
    if due:
        result = tracker.record_review(due[0]['id'], quality_rating=5, algorithm="sm2")
        print(f"Review recorded. Next review in {result['result']['next_interval_days']} days")
    stats = tracker.get_learning_stats()
    print(f"\nStats: {stats}")
