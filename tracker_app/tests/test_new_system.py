"""
Test Suite for New Learning Tracker System
Validates that SM-2 algorithm and learning tracker work correctly with isolated DB.
"""

import unittest
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tracker_app.learning.sm2_memory_model import SM2Item, SM2Scheduler, LeitnerSystem, format_next_review
from tracker_app.learning.learning_tracker import LearningTracker
from tracker_app.db import models
from tracker_app.db.models import Base

class TestSM2Algorithm(unittest.TestCase):
    def test_item_creation(self):
        item = SM2Item(item_id="test_001", question="What is X?", answer="X is...")
        self.assertEqual(item.item_id, "test_001")
        self.assertEqual(item.repetitions, 0)
        self.assertEqual(item.ease_factor, 2.5)

    def test_first_review_perfect(self):
        item = SM2Item("test", "Q?", "A")
        result = SM2Scheduler.calculate_next_interval(item, quality=5)
        self.assertEqual(item.repetitions, 1)
        self.assertEqual(result['next_interval_days'], 1)
        self.assertEqual(item.correct_count, 1)

class TestLearningTrackerModule(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.orig_session = models.SessionLocal
        models.SessionLocal = self.SessionLocal
        Base.metadata.create_all(self.engine)
        self.tracker = LearningTracker()

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        models.SessionLocal = self.orig_session

    def test_add_item(self):
        item_id = self.tracker.add_learning_item("Test Q?", "Test A", "medium")
        self.assertIsNotNone(item_id)
        item = self.tracker.get_item(item_id)
        self.assertEqual(item['question'], "Test Q?")

    def test_record_review(self):
        item_id = self.tracker.add_learning_item("Q?", "A")
        self.tracker.record_review(item_id, quality_rating=5)
        updated = self.tracker.get_item(item_id)
        self.assertEqual(updated['total_reviews'], 1)

    def test_statistics(self):
        for i in range(5):
            self.tracker.add_learning_item(f"Q{i}?", f"A{i}")
        stats = self.tracker.get_learning_stats()
        self.assertEqual(stats['total_items'], 5)

class TestUtilityFunctions(unittest.TestCase):
    def test_format_next_review(self):
        now = datetime.now()
        self.assertEqual(format_next_review(now), "NOW")
        
        tomorrow = datetime.now() + timedelta(days=1)
        # Handle small time drifts 
        text = format_next_review(tomorrow)
        self.assertTrue("tomorrow" in text or "in 23 hours" in text or "in 1 day" in text)

class TestScenarios(TestLearningTrackerModule):
    def test_complete_learning_cycle(self):
        item_id = self.tracker.add_learning_item("What is Python?", "A language", "easy")
        for i in range(6):
            self.tracker.record_review(item_id, quality_rating=5)
        item = self.tracker.get_item(item_id)
        self.assertEqual(item['status'], 'mastered')

if __name__ == '__main__':
    unittest.main()
