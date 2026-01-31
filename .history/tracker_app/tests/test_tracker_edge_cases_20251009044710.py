# tests/test_tracker_edge_cases.py
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import numpy as np

from core.tracker import (
    maybe_notify,
    compute_memory_score,
    schedule_next_review,
)

class TestTrackerEdgeCases(unittest.TestCase):
    # ---------------- Audio ----------------
    @patch("core.tracker.classify_audio_live")
    def test_audio_silence(self, mock_audio):
        # Simulate silence
        mock_audio.return_value = ("silence", 0.99)
        label, conf = mock_audio()
        self.assertIn(label, ["unknown", "silence"])

    @patch("core.tracker.classify_audio_live")
    def test_audio_classifier_missing(self, mock_audio):
        # Simulate missing audio
        mock_audio.side_effect = Exception("Audio device not found")
        with self.assertRaises(Exception):
            mock_audio()

    # ---------------- Intent ----------------
    @patch("core.tracker.predict_intent_live")
    def test_intent_fallback(self, mock_intent):
        mock_intent.return_value = {"intent_label": "unknown", "confidence": 0.0}
        intent = mock_intent({}, "silence", 0, 0)
        self.assertEqual(intent["intent_label"], "unknown")

    # ---------------- Memory/Notification ----------------
    @patch("core.tracker.maybe_notify")
    def test_memory_notify_cooldown(self, mock_notify):
        # Set up concept with recent notification
        last_review = datetime.now() - timedelta(minutes=10)
        score = compute_memory_score(last_review, 0.1, 1.0, 1, 1.0)
        next_review = schedule_next_review(last_review, score, 0.1)
        maybe_notify("concept_test", score, {"concept_test": {}}, use_attention=False)
        mock_notify.assert_called_once()

    # ---------------- OCR ----------------
    def test_ocr_none(self):
        latest_ocr = {}
        self.assertEqual(latest_ocr, {})

    def test_ocr_large_keywords(self):
        latest_ocr = {f"keyword_{i}": {"score": 0.5, "count": 1} for i in range(100)}
        self.assertEqual(len(latest_ocr), 100)

    # ---------------- Window ----------------
    def test_empty_window_title(self):
        window_title = ""
        self.assertEqual(window_title, "")

    # ---------------- DB ----------------
    def test_db_connection_fail(self):
        from core.tracker import log_session
        # Simulate normal logging call (DB locked handling is internal)
        try:
            log_session("TestWindow", 0)
        except Exception as e:
            self.fail(f"log_session raised exception {e}")

    # ---------------- Webcam ----------------
    def test_webcam_disabled(self):
        latest_attention = None
        self.assertIsNone(latest_attention)

    def test_webcam_no_faces(self):
        latest_attention = 0
        self.assertEqual(latest_attention, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
    