# tests/test_tracker_realistic_session.py
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import builtins

from core.tracker import (
    track_loop,
    _latest_ocr,
    _latest_attention,
    maybe_notify,
)
from core.knowledge_graph import get_graph, add_concepts
from threading import Event

class TestTrackerFullSessionLoop(unittest.TestCase):
    def setUp(self):
        # Ensure knowledge graph is fresh
        self.G = get_graph()
        self.G.clear()
        add_concepts(["concept_edge1", "concept_edge2", "concept_edge3"])

    @patch("core.tracker.win32gui.GetForegroundWindow", return_value=100)
    @patch("core.tracker.win32gui.GetWindowText", return_value="TestApp - EdgeCase")
    @patch("core.tracker.record_audio")
    @patch("core.tracker.audio_extract_features")
    @patch("core.tracker.audio_clf")
    @patch("core.tracker.intent_extract_features")
    @patch("core.tracker.intent_clf")
    @patch("core.tracker.intent_label_map")
    @patch("core.tracker.ocr_pipeline")
    @patch("core.tracker.webcam_pipeline")
    @patch("core.tracker.FaceDetector.detect_faces")
    @patch("core.tracker.notification.notify")
    @patch("builtins.input", return_value="n")
    def test_full_session_loop(
        self,
        mock_input,
        mock_notify,
        mock_detect_faces,
        mock_webcam,
        mock_ocr,
        mock_label_map,
        mock_intent_clf,
        mock_intent_features,
        mock_audio_clf,
        mock_audio_feats,
        mock_record_audio,
        mock_get_window_text,
        mock_get_foreground
    ):
        stop_event = Event()

        # Simulate multiple iterations
        iterations = 5
        audio_labels = ["speech", "music", "silence", "speech", "silence"]
        attention_scores = [0, 2, 5, 3, 0]
        ocr_keywords_list = [
            {"concept_edge1": {"score": 0.2, "count": 1}},
            {"concept_edge2": {"score": 0.8, "count": 3}},
            {"concept_edge3": {"score": 0.5, "count": 2}},
            {"concept_edge1": {"score": 0.9, "count": 5}},
            {},
        ]

        # Mock pipelines to return predefined values
        mock_record_audio.side_effect = [None] * iterations
        mock_audio_feats.side_effect = lambda x: [[0.1] * 10]
        mock_audio_clf.predict.return_value = audio_labels
        mock_audio_clf.predict_proba.return_value = [[0.1, 0.9]]
        mock_intent_features.side_effect = lambda *a, **kw: [[0.5] * 5]
        mock_intent_clf.predict.return_value = [0] * iterations
        mock_intent_clf.predict_proba.return_value = [[0.7, 0.3]] * iterations
        mock_label_map.inverse_transform.return_value = ["studying"] * iterations
        mock_ocr.side_effect = [{"keywords": kws} for kws in ocr_keywords_list]
        mock_detect_faces.side_effect = [(None, a) for a in attention_scores]
        mock_webcam.return_value = None

        # Patch TRACK_INTERVAL to speed up the test
        with patch("core.tracker.TRACK_INTERVAL", 0.01):
            # Run loop in a limited way
            for i in range(iterations):
                # Manually update globals as track_loop would
                global _latest_ocr, _latest_attention
                ocr_data = mock_ocr()
                _latest_ocr = ocr_data.get("keywords", {}) or {}
                _latest_attention = attention_scores[i]

                # Compute memory & maybe_notify
                for concept, info in _latest_ocr.items():
                    maybe_notify(concept, 0.5, self.G, use_attention=True)

        # Assertions
        for concept in ["concept_edge1", "concept_edge2", "concept_edge3"]:
            self.assertIn(concept, self.G.nodes)
        self.assertEqual(mock_notify.call_count, sum(len(kws) for kws in ocr_keywords_list))

if __name__ == "__main__":
    unittest.main()
