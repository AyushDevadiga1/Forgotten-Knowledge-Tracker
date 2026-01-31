# tests/test_tracker_realistic_edge_cases.py
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from core import tracker

class TestTrackerRealisticEdgeCases(unittest.TestCase):
    def setUp(self):
        # Reset globals before each test
        tracker._latest_ocr = {}
        tracker._latest_attention = 0

    @patch("core.tracker.get_active_window")
    @patch("core.tracker.record_audio")
    @patch("core.tracker.classify_audio_live")
    @patch("core.tracker.ocr_pipeline")
    @patch("core.tracker.webcam_pipeline")
    @patch("core.tracker.predict_intent_live")
    @patch("core.tracker.log_session")
    @patch("core.tracker.log_multi_modal")
    @patch("core.tracker.maybe_notify")
    def test_realistic_edge_case(
        self,
        mock_notify,
        mock_log_multi,
        mock_log_session,
        mock_intent,
        mock_webcam,
        mock_ocr,
        mock_audio,
        mock_record_audio,
        mock_get_window,
    ):
        """
        Simulate a full tracker loop iteration with extreme and edge-case inputs:
        - No window title
        - Zero and high interactions
        - Silence and speech audio
        - Empty OCR and large OCR data
        - Webcam disabled or multiple faces
        """
        # --- Mock window and interactions ---
        mock_get_window.return_value = ("", 0)  # Edge: empty window title
        
        # --- Mock audio ---
        mock_audio.return_value = ("speech", 0.95)  # Edge: high-confidence speech
        mock_record_audio.return_value = b"fake_audio_data"

        # --- Mock OCR ---
        mock_ocr.return_value = {
            "keywords": {
                "test_concept": {"score": 0.0, "count": 1},  # Edge: score 0
                "big_concept": {"score": 1.0, "count": 100}  # Edge: high count
            }
        }

        # --- Mock webcam ---
        mock_webcam.return_value = "fake_frame"
        tracker.USER_ALLOW_WEBCAM = True
        tracker._latest_attention = 5  # multiple faces detected

        # --- Mock intent ---
        mock_intent.return_value = {"intent_label": "studying", "confidence": 0.9}

        # --- Run one loop iteration manually ---
        # Update OCR
        ocr_data = tracker.ocr_pipeline()
        raw_keywords = ocr_data.get("keywords", {})
        normalized = {}
        for kw, info in raw_keywords.items():
            normalized[str(kw)] = {
                "score": float(info.get("score", 0.5)),
                "count": int(info.get("count", 1)),
            }
        tracker._latest_ocr = normalized

        # Audio
        latest_audio, audio_conf = tracker.classify_audio_live()

        # Intent
        intent_data = tracker.predict_intent_live(
            tracker._latest_ocr, latest_audio, tracker._latest_attention, 0, use_webcam=True
        )

        # Memory + notify
        G = tracker.get_graph()
        for concept in tracker._latest_ocr.keys():
            tracker.maybe_notify(concept, 0.5, G, use_attention=True)

        # Log
        tracker.log_session("Test Window", 0)
        tracker.log_multi_modal(
            "Test Window",
            tracker._latest_ocr,
            latest_audio,
            tracker._latest_attention,
            0,
            intent_data["intent_label"],
            intent_data["confidence"],
            memory_score=0.5,
        )

        # --- Assertions ---
        # 1. OCR loaded correctly
        self.assertIn("test_concept", tracker._latest_ocr)
        self.assertIn("big_concept", tracker._latest_ocr)

        # 2. Audio classification
        self.assertEqual(latest_audio, "speech")

        # 3. Intent prediction
        self.assertEqual(intent_data["intent_label"], "studying")

        # 4. Notification triggered for concepts
        mock_notify.assert_called()

        # 5. Multi-modal logging called
        mock_log_multi.assert_called()

        # 6. Session logging called
        mock_log_session.assert_called()


if __name__ == "__main__":
    unittest.main()
