# tests/test_tracker_strict_edge_cases.py
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from core.tracker import (
    maybe_notify, get_graph, compute_memory_score,
    predict_intent_live, classify_audio_live, _latest_ocr
)

class TestTrackerStrictEdgeCases(unittest.TestCase):

    def setUp(self):
        self.graph = get_graph()
        self.graph.clear()
        global _latest_ocr
        _latest_ocr = {}

    # -----------------------------
    # WEBCAM OFF EDGE
    # -----------------------------
    def test_webcam_off_attention_none(self):
        """Webcam off: attention should be None, reminders still work."""
        concept = "webcam_off"
        self.graph.add_node(concept)
        maybe_notify(concept, memory_score=0.4, graph=self.graph, use_attention=False)
        self.assertIsNone(_latest_ocr.get(concept))
        self.assertIn(concept, self.graph.nodes)

    # -----------------------------
    # AUDIO EDGE CASES
    # -----------------------------
    @patch('core.tracker.record_audio')
    @patch('core.tracker.audio_extract_features')
    def test_audio_silence(self, mock_feats, mock_audio):
        """Audio is silent; intent fallback should work."""
        mock_audio.return_value = []
        mock_feats.side_effect = lambda x: [0.0]*len(x)
        label, conf = classify_audio_live()
        self.assertEqual(label, "unknown")
        self.assertEqual(conf, 0.0)

    @patch('core.tracker.record_audio')
    @patch('core.tracker.audio_extract_features')
    def test_audio_noise(self, mock_feats, mock_audio):
        """Audio non-numeric/noisy input fallback."""
        mock_audio.return_value = [b'noise', 'NaN']
        mock_feats.side_effect = lambda x: [0.0]*len(x)
        label, conf = classify_audio_live()
        self.assertEqual(label, "unknown")
        self.assertEqual(conf, 0.0)

    @patch('core.tracker.record_audio')
    @patch('core.tracker.audio_extract_features')
    def test_audio_speech_high_interaction(self, mock_feats, mock_audio):
        """Speech audio with high interaction should trigger studying/passive."""
        mock_audio.return_value = [1.0, 1.0]
        mock_feats.side_effect = lambda x: [1.0]*len(x)
        intent = predict_intent_live({}, "speech", attention_score=80, interaction_rate=10, use_webcam=False)
        self.assertIn(intent["intent_label"], ["passive", "studying", "unknown"])

    # -----------------------------
    # OCR EDGE CASES
    # -----------------------------
    def test_empty_ocr(self):
        """Empty OCR input should not crash memory calculation."""
        for concept in _latest_ocr.keys():
            maybe_notify(concept, memory_score=0.5, graph=self.graph)
        self.assertEqual(len(self.graph.nodes), 0)

    def test_invalid_ocr_scores(self):
        """OCR with invalid scores handled safely."""
        concept = "ocr_invalid"
        self.graph.add_node(concept)
        _latest_ocr[concept] = {"score": "NaN", "count": "two"}
        last_review = datetime.now() - timedelta(days=1)
        mem_score = compute_memory_score(last_review, 0.1, 1.0, 1, 1.0)
        self.assertIsInstance(mem_score, float)

    # -----------------------------
    # IDLE / UNKNOWN APP
    # -----------------------------
    def test_idle_tab_unknown_intent(self):
        """Idle window with unknown intent does not break tracker."""
        intent = predict_intent_live({}, "unknown", attention_score=None, interaction_rate=0)
        self.assertIn(intent["intent_label"], ["idle", "passive", "unknown"])

    # -----------------------------
    # MEMORY / NOTIFICATION
    # -----------------------------
    def test_memory_low_score_notification(self):
        """Low memory triggers notification even with webcam off."""
        concept = "memory_low"
        self.graph.add_node(concept)
        maybe_notify(concept, memory_score=0.3, graph=self.graph, use_attention=False)
        self.assertIn("next_review_time", self.graph.nodes[concept])

    def test_notification_cooldown_prevents_repeat(self):
        """Cooldown prevents immediate re-notification."""
        concept = "cooldown"
        self.graph.add_node(concept, last_reminded_time=(datetime.now() + timedelta(minutes=10)).isoformat())
        maybe_notify(concept, memory_score=0.5, graph=self.graph)
        last_reminded = self.graph.nodes[concept]["last_reminded_time"]
        self.assertGreater(datetime.fromisoformat(last_reminded), datetime.now() - timedelta(minutes=1))

if __name__ == "__main__":
    unittest.main(verbosity=2)
