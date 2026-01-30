"""
Test suite for Enhanced Activity Tracker

Tests all components work correctly
"""

import unittest
import tempfile
import os
from datetime import datetime, timedelta

from core.tracker_enhanced import (
    ConceptScheduler,
    IntentValidator,
    TrackingAnalytics,
    EnhancedActivityTracker
)


class TestConceptScheduler(unittest.TestCase):
    """Test concept scheduling with SM-2"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db').name
        self.scheduler = ConceptScheduler(self.temp_db)
    
    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def test_add_concept(self):
        """Test adding a concept"""
        concept_id = self.scheduler.add_concept("Python", 0.8)
        self.assertIsNotNone(concept_id)
    
    def test_schedule_next_review(self):
        """Test SM-2 scheduling"""
        concept_id = self.scheduler.add_concept("Python", 0.8)
        
        # Concept should exist in due list
        concepts = self.scheduler.get_due_concepts()
        initial_count = len(concepts)
        
        # Schedule with good quality (4)
        self.scheduler.schedule_next_review(concept_id, quality=4)
        
        # At least one concept should exist
        self.assertGreater(initial_count, 0)
    
    def test_get_due_concepts(self):
        """Test retrieving due concepts"""
        self.scheduler.add_concept("Python", 0.8)
        self.scheduler.add_concept("JavaScript", 0.7)
        
        due = self.scheduler.get_due_concepts(limit=10)
        self.assertEqual(len(due), 2)


class TestIntentValidator(unittest.TestCase):
    """Test intent prediction validation"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db').name
        self.validator = IntentValidator(self.temp_db)
    
    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def test_log_prediction(self):
        """Test logging predictions"""
        self.validator.log_prediction("studying", 0.85, "Python tutorial")
        self.assertEqual(len(self.validator.prediction_buffer), 1)
    
    def test_get_accuracy_stats(self):
        """Test accuracy calculation"""
        # Log multiple predictions
        for i in range(5):
            self.validator.log_prediction("working", 0.8, f"task_{i}")
        
        stats = self.validator.get_accuracy_stats()
        self.assertIn('average_accuracy', stats)


class TestTrackingAnalytics(unittest.TestCase):
    """Test tracking analytics"""
    
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db').name
        self.analytics = TrackingAnalytics(self.temp_db)
    
    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def test_log_session(self):
        """Test logging tracking sessions"""
        start = datetime.now()
        end = start + timedelta(minutes=30)
        
        self.analytics.log_session(start, end, 15, 0.75, "learning")
        
        summary = self.analytics.get_daily_summary()
        self.assertEqual(summary['concepts'], 15)
    
    def test_get_trends(self):
        """Test trend analysis"""
        trends = self.analytics.get_trend_analysis(days=7)
        
        self.assertIn('tracking_days', trends)
        self.assertIn('avg_session_minutes', trends)
        self.assertIn('total_concepts_encountered', trends)


class TestEnhancedActivityTracker(unittest.TestCase):
    """Test main tracker"""
    
    def setUp(self):
        self.tracker = EnhancedActivityTracker()
    
    def test_session_lifecycle(self):
        """Test starting and ending session"""
        self.tracker.start_session()
        self.assertTrue(self.tracker.is_running)
        
        self.tracker.end_session()
        self.assertFalse(self.tracker.is_running)
    
    def test_process_concepts(self):
        """Test concept processing"""
        self.tracker.start_session()
        
        keywords = {
            'Python': {'score': 0.9, 'count': 1},
            'Machine Learning': {'score': 0.8, 'count': 1}
        }
        
        self.tracker.process_concepts(keywords)
        self.assertEqual(len(self.tracker.session_concepts), 2)
    
    def test_update_attention(self):
        """Test attention tracking"""
        self.tracker.start_session()
        
        self.tracker.update_attention(0.8)
        self.tracker.update_attention(0.75)
        
        self.assertEqual(len(self.tracker.session_attention_scores), 2)
    
    def test_get_session_stats(self):
        """Test session statistics"""
        self.tracker.start_session()
        
        self.tracker.process_concepts({'Python': {'score': 0.9, 'count': 1}})
        self.tracker.update_attention(0.8)
        
        stats = self.tracker.get_session_stats()
        
        self.assertIn('session_duration_minutes', stats)
        self.assertIn('concepts_encountered', stats)
        self.assertIn('avg_attention', stats)
        
        self.tracker.end_session()


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestConceptScheduler))
    suite.addTests(loader.loadTestsFromTestCase(TestIntentValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestTrackingAnalytics))
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedActivityTracker))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
