"""
Test Suite for New Learning Tracker System

Validates that SM-2 algorithm and learning tracker work correctly
"""

import unittest
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from tracker_app.core.sm2_memory_model import SM2Item, SM2Scheduler, LeitnerSystem, format_next_review
from tracker_app.core.learning_tracker import LearningTracker


class TestSM2Algorithm(unittest.TestCase):
    """Test SM-2 spaced repetition algorithm"""
    
    def test_item_creation(self):
        """Test creating an SM2Item"""
        item = SM2Item(
            item_id="test_001",
            question="What is X?",
            answer="X is..."
        )
        self.assertEqual(item.item_id, "test_001")
        self.assertEqual(item.repetitions, 0)
        self.assertEqual(item.ease_factor, 2.5)
    
    def test_first_review_perfect(self):
        """Test first review with perfect score"""
        item = SM2Item("test", "Q?", "A")
        result = SM2Scheduler.calculate_next_interval(item, quality=5)
        
        self.assertEqual(item.repetitions, 1)
        self.assertEqual(result['next_interval_days'], 1)
        self.assertEqual(item.correct_count, 1)
    
    def test_first_review_fail(self):
        """Test first review with failure"""
        item = SM2Item("test", "Q?", "A")
        result = SM2Scheduler.calculate_next_interval(item, quality=1)
        
        self.assertEqual(item.repetitions, 1)  # Still counts
        self.assertEqual(result['next_interval_days'], 1)  # Review tomorrow
        self.assertEqual(item.correct_count, 0)  # Not counted as correct
    
    def test_second_review_progression(self):
        """Test progression from review 1 to review 2"""
        item = SM2Item("test", "Q?", "A")
        
        # First review
        SM2Scheduler.calculate_next_interval(item, quality=5)
        self.assertEqual(item.repetitions, 1)
        
        # Second review
        result = SM2Scheduler.calculate_next_interval(item, quality=4)
        self.assertEqual(item.repetitions, 2)
        self.assertEqual(result['next_interval_days'], 3)  # 3 days
    
    def test_ease_factor_adjustment(self):
        """Test ease factor changes based on performance"""
        item = SM2Item("test", "Q?", "A")
        initial_ef = item.ease_factor
        
        # Perfect response increases ease
        SM2Scheduler.calculate_next_interval(item, quality=5)
        self.assertGreater(item.ease_factor, initial_ef)
        
        # Poor response decreases ease
        item2 = SM2Item("test2", "Q?", "A")
        SM2Scheduler.calculate_next_interval(item2, quality=2)
        self.assertLess(item2.ease_factor, initial_ef)
    
    def test_retention_estimation(self):
        """Test retention probability estimation"""
        item = SM2Item("test", "Q?", "A")
        
        # Before any review
        retention = SM2Scheduler.estimate_retention(item)
        self.assertEqual(retention['now'], 0.0)
        
        # After first review
        SM2Scheduler.calculate_next_interval(item, quality=5)
        retention = SM2Scheduler.estimate_retention(item)
        
        # Should decrease over time
        self.assertGreater(retention['1_day'], retention['7_days'])
        self.assertGreater(retention['7_days'], retention['30_days'])
    
    def test_quality_threshold(self):
        """Test that quality >= 3 is considered success"""
        item_pass = SM2Item("pass", "Q?", "A")
        item_fail = SM2Item("fail", "Q?", "A")
        
        SM2Scheduler.calculate_next_interval(item_pass, quality=3)
        SM2Scheduler.calculate_next_interval(item_fail, quality=2)
        
        self.assertEqual(item_pass.correct_count, 1)
        self.assertEqual(item_fail.correct_count, 0)


class TestLeitnerSystem(unittest.TestCase):
    """Test Leitner system alternative"""
    
    def test_leitner_progression(self):
        """Test Leitner box progression"""
        item = SM2Item("leitner", "Q?", "A")
        
        # Correct → move to box 2
        result = LeitnerSystem.advance_card(item, was_correct=True)
        self.assertEqual(result['box'], 2)
        self.assertEqual(result['next_interval_days'], 3)
        
        # Correct again → move to box 3
        result = LeitnerSystem.advance_card(item, was_correct=True)
        self.assertEqual(result['box'], 3)
        self.assertEqual(result['next_interval_days'], 7)
    
    def test_leitner_reset_on_fail(self):
        """Test that failure resets to box 1"""
        item = SM2Item("leitner", "Q?", "A")
        
        # Progress to box 3
        LeitnerSystem.advance_card(item, was_correct=True)
        LeitnerSystem.advance_card(item, was_correct=True)
        
        # Fail → back to box 1
        result = LeitnerSystem.advance_card(item, was_correct=False)
        self.assertEqual(result['box'], 1)
        self.assertEqual(result['next_interval_days'], 1)


class TestLearningTracker(unittest.TestCase):
    """Test learning tracker database operations"""
    
    def setUp(self):
        """Create test database"""
        self.tracker = LearningTracker("data/test_tracker.db")
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists("data/test_tracker.db"):
            os.remove("data/test_tracker.db")
    
    def test_add_item(self):
        """Test adding learning item"""
        item_id = self.tracker.add_learning_item(
            question="Test Q?",
            answer="Test A",
            difficulty="medium"
        )
        self.assertIsNotNone(item_id)
        
        item = self.tracker.get_item(item_id)
        self.assertEqual(item['question'], "Test Q?")
        self.assertEqual(item['difficulty'], "medium")
    
    def test_get_items_due(self):
        """Test getting items due for review"""
        id1 = self.tracker.add_learning_item("Q1?", "A1")
        id2 = self.tracker.add_learning_item("Q2?", "A2")
        
        due_items = self.tracker.get_items_due()
        self.assertGreaterEqual(len(due_items), 2)
    
    def test_record_review(self):
        """Test recording review and calculating next interval"""
        item_id = self.tracker.add_learning_item("Q?", "A")
        
        result = self.tracker.record_review(item_id, quality_rating=5)
        
        updated = self.tracker.get_item(item_id)
        self.assertEqual(updated['total_reviews'], 1)
        self.assertEqual(updated['correct_count'], 1)
        self.assertEqual(updated['repetitions'], 1)
    
    def test_statistics(self):
        """Test statistics calculation"""
        # Add multiple items
        for i in range(5):
            self.tracker.add_learning_item(f"Q{i}?", f"A{i}")
        
        stats = self.tracker.get_learning_stats()
        self.assertEqual(stats['total_items'], 5)
        self.assertEqual(stats['active_items'], 5)
        self.assertEqual(stats['mastered_items'], 0)
        self.assertGreaterEqual(stats['due_now'], 5)
    
    def test_export_json(self):
        """Test exporting items as JSON"""
        self.tracker.add_learning_item("Q1?", "A1")
        self.tracker.add_learning_item("Q2?", "A2")
        
        export = self.tracker.export_items(format="json")
        self.assertIsNotNone(export)
        self.assertIn("Q1?", export)
    
    def test_archive_item(self):
        """Test archiving item"""
        item_id = self.tracker.add_learning_item("Q?", "A")
        
        self.tracker.archive_item(item_id)
        item = self.tracker.get_item(item_id)
        self.assertEqual(item['status'], 'archived')
        
        self.tracker.unarchive_item(item_id)
        item = self.tracker.get_item(item_id)
        self.assertEqual(item['status'], 'active')
    
    def test_search(self):
        """Test searching items"""
        self.tracker.add_learning_item("Python lists", "Collections")
        self.tracker.add_learning_item("Python dicts", "Key-value")
        
        results = self.tracker.search_items("Python")
        self.assertEqual(len(results), 2)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility and formatting functions"""
    
    def test_format_next_review(self):
        """Test human-readable date formatting"""
        # Now
        now = datetime.now()
        text = format_next_review(now)
        self.assertEqual(text, "NOW")
        
        # Tomorrow
        tomorrow = datetime.now() + timedelta(days=1)
        text = format_next_review(tomorrow)
        self.assertEqual(text, "tomorrow")
        
        # In 3 days
        future = datetime.now() + timedelta(days=3)
        text = format_next_review(future)
        self.assertIn("days", text)


class TestScenarios(unittest.TestCase):
    """Test realistic learning scenarios"""
    
    def setUp(self):
        self.tracker = LearningTracker("data/test_scenarios.db")
    
    def tearDown(self):
        if os.path.exists("data/test_scenarios.db"):
            os.remove("data/test_scenarios.db")
    
    def test_complete_learning_cycle(self):
        """Test adding, reviewing, and mastering an item"""
        # Add item
        item_id = self.tracker.add_learning_item(
            question="What is Python?",
            answer="A programming language",
            difficulty="easy"
        )
        
        stats_before = self.tracker.get_learning_stats()
        self.assertEqual(stats_before['active_items'], 1)
        
        # Review 5 times (perfect score each time)
        for i in range(5):
            self.tracker.record_review(item_id, quality_rating=5)
        
        # Check item status
        item = self.tracker.get_item(item_id)
        self.assertEqual(item['total_reviews'], 5)
        self.assertEqual(item['correct_count'], 5)
        self.assertEqual(item['success_rate'], 1.0)
        self.assertEqual(item['status'], 'mastered')
        
        stats_after = self.tracker.get_learning_stats()
        self.assertEqual(stats_after['mastered_items'], 1)
    
    def test_struggling_with_item(self):
        """Test reviewing difficult item with mixed results"""
        item_id = self.tracker.add_learning_item(
            question="Complex question",
            answer="Complex answer"
        )
        
        # Mix of good and bad responses
        responses = [2, 4, 2, 5, 4, 5]
        
        for quality in responses:
            self.tracker.record_review(item_id, quality_rating=quality)
        
        item = self.tracker.get_item(item_id)
        self.assertEqual(item['total_reviews'], 6)
        self.assertGreater(item['correct_count'], 0)
        self.assertLess(item['correct_count'], 6)
        self.assertGreater(item['success_rate'], 0.3)


def run_tests(verbosity=2):
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSM2Algorithm))
    suite.addTests(loader.loadTestsFromTestCase(TestLeitnerSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestLearningTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilityFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestScenarios))
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("="*60)
    print("🧪 NEW LEARNING TRACKER - TEST SUITE")
    print("="*60)
    
    success = run_tests(verbosity=2)
    
    if success:
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("❌ SOME TESTS FAILED")
        print("="*60)
        sys.exit(1)
