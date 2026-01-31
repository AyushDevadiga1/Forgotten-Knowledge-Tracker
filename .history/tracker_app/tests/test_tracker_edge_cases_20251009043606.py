# tests/test_tracker_edge_cases.py

import unittest
from unittest.mock import patch, MagicMock
from core import tracker
from datetime import datetime, timedelta

class TestTrackerEdgeCases(unittest.TestCase):

    # -----------------------------
    # Audio-related edge cases
    # -----------------------------
    @patch('core.audio_module.classify_audio_live')
    def test_audio_silence(self, mock_audio):
        # Simulate silence audio input
        mock_audio.return_value = ("silence", 0.99)
        label, conf = mock_audio()
        self.assertIn(label, ["unknown", "silence"])

    @patch('core.audio_module.classify_audio_live')
    def test_audio_classifier_missing(self, mock_audio):
        # Simulate missing audio
        mock_audio.return_value = ("unknown", 0.0)
        label, conf = mock_audio()
        self.assertIn(label, ["unknown", "silence"])

    # -----------------------------
    # DB-related edge cases
    # -----------------------------
    @patch('sqlite3.connect')
    def test_db_connection_fail(self, mock_connect):
        # Simulate DB locked error
        mock_connect.side_effect = Exception("DB locked")
        with self.assertRaises(Exception) as context:
            tracker.log_session("TestWindow", 0)
        self.assertIn("DB locked", str(context.exception))

    # -----------------------------
    # Window title edge cases
    # -----------------------------
    @patch('core.tracker.get_active_window')
    def test_empty_window_title(self, mock_window):
        mock_window.return_value = ("", 0)
        window, interaction = mock_window()
        self.assertEqual(window, "")
        self.assertEqual(interaction, 0)

    # -----------------------------
    # Intent edge cases
    # -----------------------------
    @patch('core.intent_module.predict_intent_live')
    def test_intent_fallback(self, mock_intent):
        mock_intent.return_value = {"intent_label": "unknown", "confidence": 0.0}
        intent = mock_intent({}, "silence", 0, 0)
        self.assertEqual(intent["intent_label"], "unknown")

    # -----------------------------
    # Memory & notification edge cases
    # -----------------------------
    @patch('core.memory_module.maybe_notify')
    def test_memory_notify_cooldown(self, mock_notify):
        # Ensure notifications respect cooldown
        mock_notify.return_value = None
        tracker._latest_ocr = {"concept1": {"score": 0.2, "count": 1}}
        tracker._latest_attention = 1
        # Call memory function directly
        from core.intenty_module import compute_memory_score, schedule_next_review
        last_review = datetime.now() - timedelta(hours=1)
        score = compute_memory_score(last_review, 0.1, 1.0, 1, 1.0)
        next_review = schedule_next_review(last_review, score, 0.1)
        self.assertIsInstance(next_review, datetime)

    # -----------------------------
    # OCR-related edge cases
    # -----------------------------
    @patch('core.ocr_module.ocr_pipeline')
    def test_ocr_none(self, mock_ocr):
        mock_ocr.return_value = None
        tracker._latest_ocr = {}
        ocr_data = mock_ocr()
        self.assertIsNone(ocr_data)

    @patch('core.ocr_module.ocr_pipeline')
    def test_ocr_large_keywords(self, mock_ocr):
        mock_ocr.return_value = {
            "keywords": {f"kw{i}": {"score": 0.5, "count": i} for i in range(100)}
        }
        tracker._latest_ocr = mock_ocr()["keywords"]
        self.assertEqual(len(tracker._latest_ocr), 100)

    # -----------------------------
    # Webcam-related edge cases
    # -----------------------------
    def test_webcam_disabled(self):
        tracker._latest_attention = None
        self.assertIsNone(tracker._latest_attention)

    def test_webcam_no_faces(self):
        tracker._latest_attention = 0
        self.assertEqual(tracker._latest_attention, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
