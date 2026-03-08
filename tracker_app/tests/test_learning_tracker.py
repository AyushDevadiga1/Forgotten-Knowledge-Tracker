"""
Unit Tests: LearningTracker
============================
Tests core CRUD and review logic with isolated SQLAlchemy in-memory DB.
Run: python -m pytest tracker_app/tests/test_learning_tracker.py -v
"""

import unittest
import json
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tracker_app.learning.learning_tracker import LearningTracker
from tracker_app.db import models
from tracker_app.db.models import Base, LearningItem, ReviewHistory

class TestLearningTrackerBase(unittest.TestCase):
    def setUp(self):
        # Create isolated in-memory engine and session
        self.engine = create_engine('sqlite:///:memory:')
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Patch the global SessionLocal that LearningTracker uses
        self.orig_session = models.SessionLocal
        models.SessionLocal = self.SessionLocal
        
        Base.metadata.create_all(self.engine)
        self.tracker = LearningTracker()

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        models.SessionLocal = self.orig_session

class TestAddLearningItem(TestLearningTrackerBase):
    def test_add_valid_item_returns_id(self):
        item_id = self.tracker.add_learning_item("Q?", "A.")
        self.assertIsInstance(item_id, str)
        self.assertGreater(len(item_id), 0)

    def test_add_item_persisted_in_db(self):
        self.tracker.add_learning_item("What is recursion?", "A function calls itself")
        with self.SessionLocal() as db:
            item = db.query(LearningItem).first()
            self.assertIsNotNone(item)
            self.assertEqual(item.question, "What is recursion?")

class TestGetItemsDue(TestLearningTrackerBase):
    def test_empty_db_returns_empty_list(self):
        result = self.tracker.get_items_due()
        self.assertEqual(len(result), 0)

    def test_new_item_is_immediately_due(self):
        self.tracker.add_learning_item("Q?", "A.")
        due = self.tracker.get_items_due()
        self.assertEqual(len(due), 1)

class TestGetLearningStats(TestLearningTrackerBase):
    def test_stats_with_empty_db(self):
        stats = self.tracker.get_learning_stats()
        self.assertEqual(stats['total_items'], 0)

    def test_stats_reflect_added_items(self):
        self.tracker.add_learning_item("Q1", "A1")
        self.tracker.add_learning_item("Q2", "A2")
        stats = self.tracker.get_learning_stats()
        self.assertEqual(stats['total_items'], 2)

class TestRecordReview(TestLearningTrackerBase):
    def test_review_updates_repetitions(self):
        item_id = self.tracker.add_learning_item("Q?", "A.")
        self.tracker.record_review(item_id, quality_rating=5)
        with self.SessionLocal() as db:
            item = db.query(LearningItem).filter(LearningItem.id == item_id).first()
            self.assertGreater(item.repetitions, 0)

    def test_review_history_recorded(self):
        item_id = self.tracker.add_learning_item("Q?", "A.")
        self.tracker.record_review(item_id, quality_rating=3)
        with self.SessionLocal() as db:
            count = db.query(ReviewHistory).filter(ReviewHistory.item_id == item_id).count()
            self.assertEqual(count, 1)

if __name__ == '__main__':
    unittest.main()


if __name__ == '__main__':
    unittest.main(verbosity=2)
