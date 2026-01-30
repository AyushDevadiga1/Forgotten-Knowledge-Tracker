"""
Learning Tracker - User-Controlled Learning Management System

This replaces the surveillance-based tracking with explicit user input.
Users control what they learn, and the system manages spaced repetition.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

from core.sm2_memory_model import SM2Item, SM2Scheduler, LeitnerSystem
from config import DATA_DIR

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
    
    This is the core of the new simplified system.
    Users explicitly log what they want to learn.
    """
    
    def __init__(self, db_path: str = None):
        """Initialize learning tracker with database"""
        self.db_path = db_path or str(DATA_DIR / "learning_tracker.db")
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        # Learning items table
        c.execute('''
            CREATE TABLE IF NOT EXISTS learning_items (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                item_type TEXT NOT NULL,
                tags TEXT,
                
                -- SM-2 Algorithm State
                interval INTEGER DEFAULT 0,
                ease_factor REAL DEFAULT 2.5,
                repetitions INTEGER DEFAULT 0,
                next_review_date TEXT NOT NULL,
                last_review_date TEXT,
                
                -- Statistics
                total_reviews INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                
                -- Status
                status TEXT DEFAULT 'active',  -- active, mastered, archived
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Review history table
        c.execute('''
            CREATE TABLE IF NOT EXISTS review_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                review_date TEXT NOT NULL,
                quality_rating INTEGER NOT NULL,
                correct BOOLEAN NOT NULL,
                ease_factor REAL NOT NULL,
                interval_days INTEGER NOT NULL,
                time_spent_seconds INTEGER,
                
                FOREIGN KEY(item_id) REFERENCES learning_items(id)
            )
        ''')
        
        # Learning sessions table (optional, for analytics)
        c.execute('''
            CREATE TABLE IF NOT EXISTS learning_sessions (
                id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                items_reviewed INTEGER DEFAULT 0,
                items_correct INTEGER DEFAULT 0,
                duration_seconds INTEGER,
                notes TEXT
            )
        ''')
        
        # Create indexes for performance
        c.execute('CREATE INDEX IF NOT EXISTS idx_next_review ON learning_items(next_review_date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_status ON learning_items(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_item_reviews ON review_history(item_id)')
        
        conn.commit()
        conn.close()
    
    def add_learning_item(
        self,
        question: str,
        answer: str,
        difficulty: str = "medium",
        item_type: str = "concept",
        tags: List[str] = None
    ) -> str:
        """
        Add a new learning item.
        
        Args:
            question: What to learn (question/prompt)
            answer: The answer/explanation
            difficulty: ease, medium, or hard
            item_type: Type of learning content
            tags: Optional tags for categorization
        
        Returns:
            Item ID for future reference
        """
        item_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO learning_items
            (id, created_at, question, answer, difficulty, item_type, tags, next_review_date, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item_id,
            now,
            question,
            answer,
            difficulty,
            item_type,
            json.dumps(tags or []),
            now,  # Schedule first review for now
            now
        ))
        
        conn.commit()
        conn.close()
        
        return item_id
    
    def get_items_due(self) -> List[Dict[str, Any]]:
        """Get items that are due for review now"""
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM learning_items 
            WHERE status = 'active' AND next_review_date <= ?
            ORDER BY next_review_date ASC
        ''', (now,))
        
        rows = c.fetchall()
        conn.close()
        
        return [self._row_to_dict(row) for row in rows]
    
    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a single learning item by ID"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('SELECT * FROM learning_items WHERE id = ?', (item_id,))
        row = c.fetchone()
        conn.close()
        
        return self._row_to_dict(row) if row else None
    
    def record_review(
        self,
        item_id: str,
        quality_rating: int,
        time_spent_seconds: int = None,
        algorithm: str = "sm2"
    ) -> Dict[str, Any]:
        """
        Record a review attempt and update scheduling.
        
        Args:
            item_id: ID of reviewed item
            quality_rating: 0-5 scale (0=complete failure, 5=perfect)
            time_spent_seconds: How long spent on this review
            algorithm: "sm2" or "leitner"
        
        Returns:
            Updated item information with next review schedule
        """
        item_dict = self.get_item(item_id)
        if not item_dict:
            raise ValueError(f"Item {item_id} not found")
        
        # Reconstruct SM2Item from database
        item = self._dict_to_sm2item(item_dict)
        
        # Calculate next interval based on algorithm
        if algorithm == "sm2":
            result = SM2Scheduler.calculate_next_interval(item, quality_rating)
        else:
            was_correct = quality_rating >= 3
            result = LeitnerSystem.advance_card(item, was_correct)
        
        # Record review
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        review_date = datetime.now().isoformat()
        was_correct = quality_rating >= 3
        
        c.execute('''
            INSERT INTO review_history
            (item_id, review_date, quality_rating, correct, ease_factor, interval_days, time_spent_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            item_id,
            review_date,
            quality_rating,
            was_correct,
            item.ease_factor,
            item.interval,
            time_spent_seconds
        ))
        
        # Update item
        success_rate = item.correct_count / item.total_reviews if item.total_reviews > 0 else 0
        
        # Determine status
        if success_rate > 0.95 and item.repetitions > 5:
            status = 'mastered'
        else:
            status = 'active'
        
        c.execute('''
            UPDATE learning_items SET
                interval = ?,
                ease_factor = ?,
                repetitions = ?,
                next_review_date = ?,
                last_review_date = ?,
                total_reviews = ?,
                correct_count = ?,
                success_rate = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
        ''', (
            item.interval,
            item.ease_factor,
            item.repetitions,
            item.next_review_date.isoformat(),
            review_date,
            item.total_reviews,
            item.correct_count,
            success_rate,
            status,
            datetime.now().isoformat(),
            item_id
        ))
        
        conn.commit()
        conn.close()
        
        # Return updated info
        updated_item = self.get_item(item_id)
        return {
            'item': updated_item,
            'result': result,
            'retention_estimate': SM2Scheduler.estimate_retention(item)
        }
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get overall learning statistics"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM learning_items WHERE status = "active"')
        active_count = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM learning_items WHERE status = "mastered"')
        mastered_count = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM learning_items')
        total_count = c.fetchone()[0]
        
        c.execute('''
            SELECT COUNT(*) FROM learning_items 
            WHERE status = "active" AND next_review_date <= ?
        ''', (datetime.now().isoformat(),))
        due_count = c.fetchone()[0]
        
        c.execute('SELECT AVG(success_rate) FROM learning_items')
        avg_success = c.fetchone()[0] or 0
        
        c.execute('SELECT SUM(total_reviews) FROM learning_items')
        total_reviews = c.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_items': total_count,
            'active_items': active_count,
            'mastered_items': mastered_count,
            'due_now': due_count,
            'average_success_rate': avg_success,
            'total_reviews_ever': total_reviews
        }
    
    def get_learning_today(self) -> Dict[str, Any]:
        """Get today's learning progress"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        today_end = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('''
            SELECT COUNT(*), SUM(CASE WHEN correct THEN 1 ELSE 0 END)
            FROM review_history
            WHERE review_date >= ? AND review_date <= ?
        ''', (today_start, today_end))
        
        total_reviews, correct_reviews = c.fetchone()
        correct_reviews = correct_reviews or 0
        
        conn.close()
        
        return {
            'reviews_today': total_reviews or 0,
            'correct_today': correct_reviews,
            'accuracy_today': (correct_reviews / total_reviews * 100) if total_reviews else 0
        }
    
    def search_items(self, query: str) -> List[Dict[str, Any]]:
        """Search learning items by question"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        search_term = f"%{query}%"
        c.execute('''
            SELECT * FROM learning_items
            WHERE status = "active" AND (question LIKE ? OR answer LIKE ?)
            ORDER BY created_at DESC
        ''', (search_term, search_term))
        
        rows = c.fetchall()
        conn.close()
        
        return [self._row_to_dict(row) for row in rows]
    
    def archive_item(self, item_id: str):
        """Archive (hide) an item from active review"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('''
            UPDATE learning_items SET status = "archived", updated_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), item_id))
        
        conn.commit()
        conn.close()
    
    def unarchive_item(self, item_id: str):
        """Restore an archived item"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('''
            UPDATE learning_items SET status = "active", updated_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), item_id))
        
        conn.commit()
        conn.close()
    
    def export_items(self, format: str = "json") -> str:
        """Export all learning items for backup/migration"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT * FROM learning_items ORDER BY created_at DESC')
        rows = c.fetchall()
        conn.close()
        
        items = [self._row_to_dict(row) for row in rows]
        
        if format == "json":
            return json.dumps(items, indent=2, default=str)
        elif format == "anki":
            # Export to Anki format (TSV)
            lines = []
            for item in items:
                # Anki format: question \t answer \t tags
                tags = ' '.join(json.loads(item['tags']) or [])
                lines.append(f"{item['question']}\t{item['answer']}\t{tags}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    # Helper methods
    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        if row is None:
            return None
        
        return {
            'id': row[0],
            'created_at': row[1],
            'question': row[2],
            'answer': row[3],
            'difficulty': row[4],
            'item_type': row[5],
            'tags': json.loads(row[6]) if row[6] else [],
            'interval': row[7],
            'ease_factor': row[8],
            'repetitions': row[9],
            'next_review_date': row[10],
            'last_review_date': row[11],
            'total_reviews': row[12],
            'correct_count': row[13],
            'success_rate': row[14],
            'status': row[15],
            'updated_at': row[16]
        }
    
    @staticmethod
    def _dict_to_sm2item(item_dict: Dict[str, Any]) -> SM2Item:
        """Convert database dict back to SM2Item object"""
        item = SM2Item(
            item_id=item_dict['id'],
            question=item_dict['question'],
            answer=item_dict['answer'],
            difficulty=item_dict['difficulty'],
            created_at=datetime.fromisoformat(item_dict['created_at'])
        )
        
        # Restore SM-2 state
        item.interval = item_dict['interval']
        item.ease_factor = item_dict['ease_factor']
        item.repetitions = item_dict['repetitions']
        item.next_review_date = datetime.fromisoformat(item_dict['next_review_date'])
        item.last_review_date = (
            datetime.fromisoformat(item_dict['last_review_date'])
            if item_dict['last_review_date']
            else None
        )
        item.total_reviews = item_dict['total_reviews']
        item.correct_count = item_dict['correct_count']
        
        return item


# Example usage
if __name__ == "__main__":
    tracker = LearningTracker()
    
    # Add sample items
    print("=== Learning Tracker Example ===\n")
    
    id1 = tracker.add_learning_item(
        question="What is photosynthesis?",
        answer="Process by which plants convert light to chemical energy",
        difficulty="easy",
        item_type="concept",
        tags=["biology", "plants"]
    )
    print(f"Added item: {id1}")
    
    # Get items due
    due = tracker.get_items_due()
    print(f"\nItems due for review: {len(due)}")
    
    # Simulate review
    if due:
        result = tracker.record_review(due[0]['id'], quality_rating=5, algorithm="sm2")
        print(f"Review recorded. Next review in {result['result']['next_interval_days']} days")
    
    # Show stats
    stats = tracker.get_learning_stats()
    print(f"\nStats: {stats}")
