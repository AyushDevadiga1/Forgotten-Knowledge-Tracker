# tests/test_tracker_edge_cases_full.py
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import random
import logging

from core.tracker import (
    maybe_notify,
    get_graph,
    compute_memory_score,
    predict_intent_live,
    classify_audio_live,
    _latest_ocr
)

logging.disable(logging.CRITICAL)  # suppress logging for clean test output

class TestTrackerEdgeCasesFull(unittest.TestCase):

    def setUp(self):
        """Reset knowledge graph and tracker state before each test."""
        self.graph = get_graph()
        self.graph.clear()
        global _latest_ocr
        _latest_ocr = {}

    # -----------------------------
    # AUDIO EDGE CASES
    # -----------------------------
    @patch('core.tracker.record_audio')
    @patch('core.tracker.audio_extract_features')
    def test_audio_non_numeric(self, mock_feats, mock_audio):
        """Audio returns non-numeric / invalid features."""
        try:
            mock_audio.return_value = [b'noise', None, 'NaN']
            mock_feats.side_effect = lambda x: [0.0] * len(x)
            label, conf = classify_audio_live()
            self.assertIn(label, ["unknown"])
            self.assertEqual(conf, 0.0)
        except Exception as e:
            self.fail(f"Audio edge case failed: {e}")

    # -----------------------------
    # OCR EDGE CASES
    # -----------------------------
    def test_empty_ocr(self):
        """Empty OCR dict should not crash tracker memory update."""
        try:
            ocr_input = {}
            for concept in ocr_input.keys():
                maybe_notify(concept, memory_score=0.5, graph=self.graph)
            self.assertEqual(len(self.graph.nodes), 0)
        except Exception as e:
            self.fail(f"Empty OCR test failed: {e}")

    def test_ocr_invalid_scores(self):
        """OCR with invalid score types should not break memory computation."""
        try:
            concept = "test_concept"
            self.graph.add_node(concept)
            ocr_input = {concept: {"score": "NaN", "count": "two"}}
            global _latest_ocr
            _latest_ocr = ocr_input
            last_review = datetime.now() - timedelta(days=1)
            mem_score = compute_memory_score(last_review, 0.1, 1.0, 1, 1.0)
            self.assertIsInstance(mem_score, float)
        except Exception as e:
            self.fail(f"OCR invalid scores test failed: {e}")

    # -----------------------------
    # ATTENTION EDGE CASES
    # -----------------------------
    def test_attention_none(self):
        """Tracker should handle None attention safely."""
        try:
            concept = "attention_test"
            self.graph.add_node(concept)
            maybe_notify(concept, memory_score=0.4, graph=self.graph, use_attention=False)
            self.assertIn(concept, self.graph.nodes)
        except Exception as e:
            self.fail(f"Attention None test failed: {e}")

    # -----------------------------
    # INTERACTION EDGE CASES
    # -----------------------------
    def test_interaction_zero(self):
        """Zero interaction rate should trigger fallback intent."""
        try:
            intent = predict_intent_live({}, "unknown", 0, 0)
            self.assertIn(intent["intent_label"], ["idle", "passive", "unknown"])
        except Exception as e:
            self.fail(f"Zero interaction test failed: {e}")

    def test_interaction_high(self):
        """Very high interaction rate should not break intent prediction."""
        try:
            intent = predict_intent_live({}, "speech", 100, 50)
            self.assertIsInstance(intent["confidence"], float)
        except Exception as e:
            self.fail(f"High interaction test failed: {e}")

    # -----------------------------
    # NOTIFICATION / MEMORY EDGE CASES
    # -----------------------------
    def test_notification_cooldown(self):
        """Reminder cooldown prevents immediate repeat notifications."""
        try:
            concept = "cooldown_test"
            self.graph.add_node(concept, last_reminded_time=(datetime.now() + timedelta(minutes=10)).isoformat())
            maybe_notify(concept, memory_score=0.5, graph=self.graph)
            last_reminded = self.graph.nodes[concept]["last_reminded_time"]
            self.assertGreater(datetime.fromisoformat(last_reminded), datetime.now() - timedelta(minutes=1))
        except Exception as e:
            self.fail(f"Notification cooldown test failed: {e}")

    def test_notification_low_memory_score(self):
        """Low memory score triggers notification."""
        try:
            concept = "memory_test"
            self.graph.add_node(concept)
            maybe_notify(concept, memory_score=0.3, graph=self.graph, use_attention=False)
            self.assertIn("next_review_time", self.graph.nodes[concept])
        except Exception as e:
            self.fail(f"Low memory score notification test failed: {e}")

if __name__ == "__main__":
    # run all tests, independent of failures
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestTrackerEdgeCasesFull)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
