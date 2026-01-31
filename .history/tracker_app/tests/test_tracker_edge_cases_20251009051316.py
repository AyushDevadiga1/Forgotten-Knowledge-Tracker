import unittest
from unittest.mock import patch, MagicMock
import random
import string
from datetime import datetime
import sqlite3
import os
import json
import numpy as np

from core.tracker import (
    classify_audio_live,
    predict_intent_live,
    maybe_notify,
    log_multi_modal,
    log_session,
    get_graph,
    add_concepts,
    _latest_ocr,
    _latest_attention,
    DB_PATH
)

class TestTrackerStressEdgeCases(unittest.TestCase):
    """Automated stress test: random edge inputs over multiple iterations."""

    def setUp(self):
        # Reset DB
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db
        init_db()
        init_multi_modal_db()
        init_memory_decay_db()
        _latest_ocr.clear()
        global _latest_attention
        _latest_attention = None

    def safe_audio_input(self, audio_mock):
        """Ensure audio input is safe for processing."""
        if audio_mock is None or audio_mock == b"":
            return np.array([], dtype=float)
        try:
            return np.frombuffer(audio_mock, dtype=np.float32)
        except Exception:
            return np.array([], dtype=float)

    @patch("core.tracker.record_audio")
    @patch("core.tracker.ocr_pipeline")
    @patch("core.tracker.webcam_pipeline")
    @patch("core.tracker.FaceDetector")
    @patch("core.tracker.notification.notify")
    def test_stress_tracker(
        self,
        mock_notify,
        mock_face_detector,
        mock_webcam,
        mock_ocr,
        mock_audio
    ):
        ITERATIONS = 100  # number of simulated tracker loops

        # Setup FaceDetector mock
        fd_instance = MagicMock()
        mock_face_detector.return_value = fd_instance
        fd_instance.detect_faces.side_effect = lambda frame: (["face"] * random.randint(0,3), random.randint(0,3))

        for i in range(ITERATIONS):
            # -----------------------------
            # Random OCR edge input
            # -----------------------------
            num_keywords = random.randint(0, 100)  # 0 = empty, 100 = many
            ocr_keywords = {}
            for _ in range(num_keywords):
                kw = ''.join(random.choices(string.ascii_letters, k=5))
                ocr_keywords[kw] = {"score": random.random(), "count": random.randint(1,5)}
            mock_ocr.return_value = {"keywords": ocr_keywords}
            _latest_ocr.update(ocr_keywords)

            # -----------------------------
            # Random audio input with safe handling
            # -----------------------------
            raw_audio = random.choice([b"", b"noise", None])
            safe_audio = self.safe_audio_input(raw_audio)
            mock_audio.return_value = safe_audio
            audio_label, audio_conf = classify_audio_live()

            # -----------------------------
            # Random webcam/attention
            # -----------------------------
            frame = mock_webcam.return_value
            _latest_attention = random.randint(0,5)

            # -----------------------------
            # Random interaction rate
            # -----------------------------
            interaction_rate = random.randint(0,50)

            # -----------------------------
            # Memory & notifications
            # -----------------------------
            concepts = list(_latest_ocr.keys())[:5] or ["dummy_concept"]
            add_concepts(concepts)
            G = get_graph()
            for concept in concepts:
                maybe_notify(concept, memory_score=random.random(), graph=G, use_attention=True)

            # -----------------------------
            # Predict intent
            # -----------------------------
            intent_data = predict_intent_live(_latest_ocr, audio_label, _latest_attention, interaction_rate, use_webcam=True)

            # -----------------------------
            # Log multi-modal
            # -----------------------------
            log_multi_modal(
                window=f"window_{i}",
                ocr_keywords=_latest_ocr,
                audio_label=audio_label,
                attention_score=_latest_attention,
                interaction_rate=interaction_rate,
                intent_label=intent_data["intent_label"],
                intent_confidence=intent_data["confidence"],
                memory_score=random.random()
            )

        # -----------------------------
        # Assertions: DB & Graph integrity
        # -----------------------------
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Check multi-modal logs exist
        c.execute("SELECT COUNT(*) FROM multi_modal_logs")
        total_logs = c.fetchone()[0]
        self.assertEqual(total_logs, ITERATIONS)

        # Check no DB corruption (simple query)
        c.execute("SELECT * FROM multi_modal_logs LIMIT 1")
        row = c.fetchone()
        self.assertIsNotNone(row)
        conn.close()

        # Check knowledge graph integrity
        G = get_graph()
        for node in G.nodes:
            self.assertIn("memory_score", G.nodes[node])
            self.assertIn("next_review_time", G.nodes[node])
            self.assertIn("last_reminded_time", G.nodes[node])

        # Check that notifications were called (at least some iterations)
        self.assertGreater(mock_notify.call_count, 0)


if __name__ == "__main__":
    unittest.main()
