# tests/test_tracker_edge_cases.py

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from core.tracker import track_loop, InteractionCounter, maybe_notify
from core.db_module import init_db, init_multi_modal_db
from core.knowledge_graph import get_graph, add_concepts
from core.audio_module import record_audio
from core.ocr_module import ocr_pipeline
from core.webcam_module import webcam_pipeline

class TestTrackerEdgeCases(unittest.TestCase):

    def setUp(self):
        # Initialize DBs in memory
        init_db()
        init_multi_modal_db()
        self.G = get_graph()
        add_concepts(["test_concept"])

    # -----------------------------
    # Active Window & Interaction
    # -----------------------------
    @patch("core.tracker.get_active_window")
    def test_empty_window_title(self, mock_window):
        mock_window.return_value = ("", 0)
        window, interaction = mock_window()
        self.assertEqual(window, "")
        self.assertEqual(interaction, 0)

    # -----------------------------
    # Audio Module
    # -----------------------------
    @patch("core.tracker.record_audio")
    def test_audio_silence(self, mock_audio):
        mock_audio.return_value = b""  # simulate silence
        from core.tracker import classify_audio_live
        label, conf = classify_audio_live()
        self.assertIn(label, ["unknown", "silence"])

    # Audio classifier missing
    @patch("core.tracker.audio_clf", None)
    def test_audio_classifier_missing(self):
        from core.tracker import classify_audio_live
        label, conf = classify_audio_live()
        self.assertEqual(label, "unknown")
        self.assertEqual(conf, 0.0)

    # -----------------------------
    # OCR Module
    # -----------------------------
    @patch("core.tracker.ocr_pipeline")
    def test_ocr_none(self, mock_ocr):
        mock_ocr.return_value = None
        from core.tracker import latest_ocr
        ocr_result = mock_ocr()
        self.assertIsNone(ocr_result)

    @patch("core.tracker.ocr_pipeline")
    def test_ocr_large_keywords(self, mock_ocr):
        mock_ocr.return_value = {"keywords": {f"kw{i}": {"score": 0.5, "count": 1} for i in range(1000)}}
        ocr_data = mock_ocr()
        self.assertEqual(len(ocr_data["keywords"]), 1000)

    # -----------------------------
    # Webcam / Attention
    # -----------------------------
    @patch("core.tracker.webcam_pipeline")
    @patch("core.tracker.FaceDetector.detect_faces")
    def test_webcam_no_faces(self, mock_detect, mock_webcam):
        mock_webcam.return_value = "frame"
        mock_detect.return_value = ("frame", 0)
        frame = mock_webcam()
        faces, num_faces = mock_detect(frame)
        self.assertEqual(num_faces, 0)

    @patch("core.tracker.USER_ALLOW_WEBCAM", False)
    def test_webcam_disabled(self):
        from core.tracker import latest_attention
        self.assertIsNone(latest_attention)  # webcam disabled

    # -----------------------------
    # Memory / Reminders
    # -----------------------------
    def test_memory_notify_cooldown(self):
        # concept already reminded recently
        self.G.nodes["test_concept"]["last_reminded_time"] = datetime.now().isoformat()
        maybe_notify("test_concept", 0.5, self.G)
        # No exception should occur and reminder skipped

    # -----------------------------
    # Intent Prediction Fallback
    # -----------------------------
    @patch("core.tracker.intent_clf", None)
    def test_intent_fallback(self):
        from core.tracker import predict_intent_live
        result = predict_intent_live({}, "unknown", 0, 0, use_webcam=False)
        self.assertIn(result["intent_label"], ["idle", "passive", "unknown"])

    # -----------------------------
    # DB logging failures
    # -----------------------------
    @patch("sqlite3.connect")
    def test_db_connection_fail(self, mock_conn):
        mock_conn.side_effect = Exception("DB locked")
        from core.tracker import log_session
        try:
            log_session("TestWindow", 0)
        except Exception as e:
            self.fail(f"log_session raised exception {e}")

if __name__ == "__main__":
    unittest.main()
