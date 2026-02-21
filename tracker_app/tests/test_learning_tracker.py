"""
Unit Tests: LearningTracker
============================
Tests core CRUD and review logic with in-memory SQLite (no side effects).
Run: python -m pytest tracker_app/tests/test_learning_tracker.py -v
"""

import unittest
import sqlite3
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tracker_app.core.learning_tracker import LearningTracker


class TestLearningTrackerSetup(unittest.TestCase):
    """Tests that tracker initializes correctly."""

    def setUp(self):
        """Use a temp file DB so tests don't affect real data."""
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        self.tracker = LearningTracker(db_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_database_file_created(self):
        """DB file should exist after init."""
        self.assertTrue(os.path.exists(self.tmp.name))

    def test_tables_exist(self):
        """Required tables should be created on init."""
        conn = sqlite3.connect(self.tmp.name)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in c.fetchall()}
        conn.close()
        self.assertIn('learning_items', tables, "learning_items table missing")
        self.assertIn('review_history', tables, "review_history table missing")


class TestAddLearningItem(unittest.TestCase):
    """Tests for add_learning_item()."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        self.tracker = LearningTracker(db_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_add_valid_item_returns_id(self):
        """Adding a valid item should return a non-empty string ID."""
        item_id = self.tracker.add_learning_item(
            question="What is Python?",
            answer="A high-level programming language."
        )
        self.assertIsInstance(item_id, str)
        self.assertGreater(len(item_id), 0)

    def test_add_item_persisted_in_db(self):
        """Added item should be retrievable from DB."""
        self.tracker.add_learning_item(
            question="What is recursion?",
            answer="A function that calls itself."
        )
        conn = sqlite3.connect(self.tmp.name)
        c = conn.cursor()
        c.execute("SELECT question, answer FROM learning_items")
        rows = c.fetchall()
        conn.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "What is recursion?")

    def test_add_multiple_items_unique_ids(self):
        """Each added item should have a unique ID."""
        id1 = self.tracker.add_learning_item("Q1?", "A1.")
        id2 = self.tracker.add_learning_item("Q2?", "A2.")
        id3 = self.tracker.add_learning_item("Q3?", "A3.")
        self.assertNotEqual(id1, id2)
        self.assertNotEqual(id2, id3)

    def test_add_item_with_tags(self):
        """Tags should be stored and retrievable."""
        self.tracker.add_learning_item(
            question="Q?", answer="A.",
            tags=["python", "programming"]
        )
        conn = sqlite3.connect(self.tmp.name)
        c = conn.cursor()
        c.execute("SELECT tags FROM learning_items")
        row = c.fetchone()
        conn.close()
        self.assertIn("python", row[0])

    def test_add_item_default_status_is_active(self):
        """Newly added items should have 'active' status."""
        self.tracker.add_learning_item("Q?", "A.")
        conn = sqlite3.connect(self.tmp.name)
        c = conn.cursor()
        c.execute("SELECT status FROM learning_items")
        row = c.fetchone()
        conn.close()
        self.assertEqual(row[0], 'active')


class TestGetItemsDue(unittest.TestCase):
    """Tests for get_items_due()."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        self.tracker = LearningTracker(db_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_empty_db_returns_empty_list(self):
        """With no items, get_items_due() should return []."""
        result = self.tracker.get_items_due()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_new_item_is_immediately_due(self):
        """Newly added items have next_review_date = now, so they're immediately due."""
        self.tracker.add_learning_item("Q?", "A.")
        due = self.tracker.get_items_due()
        self.assertEqual(len(due), 1)

    def test_due_items_return_correct_fields(self):
        """Due items should have expected keys."""
        self.tracker.add_learning_item("Q?", "A.")
        due = self.tracker.get_items_due()
        item = due[0]
        required_keys = ['id', 'question', 'answer', 'difficulty', 'next_review_date']
        for key in required_keys:
            self.assertIn(key, item, f"Missing key: {key}")


class TestGetLearningStats(unittest.TestCase):
    """Tests for get_learning_stats()."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        self.tracker = LearningTracker(db_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_stats_with_empty_db(self):
        """Stats should return valid zero counts with empty DB."""
        stats = self.tracker.get_learning_stats()
        self.assertIsInstance(stats, dict)
        # Should not crash and should have total_items
        self.assertIn('total_items', stats)
        self.assertEqual(stats['total_items'], 0)

    def test_stats_reflect_added_items(self):
        """Stats should count items correctly after adding."""
        self.tracker.add_learning_item("Q1?", "A1.")
        self.tracker.add_learning_item("Q2?", "A2.")
        stats = self.tracker.get_learning_stats()
        self.assertEqual(stats['total_items'], 2)


class TestRecordReview(unittest.TestCase):
    """Tests for record_review()."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        self.tracker = LearningTracker(db_path=self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_record_valid_review(self):
        """Recording a review for a valid item should not raise."""
        item_id = self.tracker.add_learning_item("Q?", "A.")
        try:
            self.tracker.record_review(item_id, quality_rating=4)
        except Exception as e:
            self.fail(f"record_review() raised an exception: {e}")

    def test_review_updates_repetitions(self):
        """After a successful review, repetitions should increase."""
        item_id = self.tracker.add_learning_item("Q?", "A.")
        self.tracker.record_review(item_id, quality_rating=5)

        conn = sqlite3.connect(self.tmp.name)
        c = conn.cursor()
        c.execute("SELECT repetitions FROM learning_items WHERE id=?", (item_id,))
        row = c.fetchone()
        conn.close()
        self.assertGreater(row[0], 0, "Repetitions should increase after a successful review")

    def test_review_history_recorded(self):
        """After a review, review_history table should have an entry."""
        item_id = self.tracker.add_learning_item("Q?", "A.")
        self.tracker.record_review(item_id, quality_rating=3)

        conn = sqlite3.connect(self.tmp.name)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM review_history WHERE item_id=?", (item_id,))
        count = c.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1, "One review history record should exist after one review")

    def test_poor_review_does_not_increase_interval_greatly(self):
        """A poor review (quality 1) should not increase the interval significantly."""
        item_id = self.tracker.add_learning_item("Q?", "A.")
        self.tracker.record_review(item_id, quality_rating=1)

        conn = sqlite3.connect(self.tmp.name)
        c = conn.cursor()
        c.execute("SELECT interval FROM learning_items WHERE id=?", (item_id,))
        row = c.fetchone()
        conn.close()
        self.assertLessEqual(row[0], 1, "Poor review should keep interval at 1 or below")


if __name__ == '__main__':
    unittest.main(verbosity=2)
