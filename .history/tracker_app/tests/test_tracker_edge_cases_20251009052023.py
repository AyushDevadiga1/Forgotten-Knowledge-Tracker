import unittest
from unittest.mock import patch, MagicMock
import random
import string
import os
import sqlite3

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

class TestTrackerIndividualInputs(unittest.TestCase):
    """Test tracker modules individually for precise debugging."""

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

    # -----------------------------
    # OCR-Only Edge Cases
    # -----------------------------
    @patch("core.tracker.ocr_pipeline")
    def test_ocr_only(self, mock_ocr):
        num_keywords = random.randint(0, 100)
        ocr_keywords = {}
        for _ in range(num_keywords):
            kw = ''.join(random.choices(string.ascii_letters, k=5))
            ocr_keywords[kw] = {"score": random.random(), "count": random.randint(1,5)}
        mock_ocr.return_value = {"keywords": ocr_keywords}
        _latest_ocr.update(ocr_keywords)

        concepts = list(_latest_ocr.keys())[:5] or ["dummy_concept"]
        add_concepts(concepts)
        G = get_graph()

        for node in G.nodes:
            self.assertIn("memory_score", G.nodes[node])
            self.assertIn("next_review_time", G.nodes[node])
            self.assertIn("last_reminded_time", G.nodes[node])

    # -----------------------------
    # Audio-Only Edge Cases
    # -----------------------------
    @patch("core.tracker.record_audio")
    def test_audio_only(self, mock_audio):
        audio_mock = random.choice([b"", b"noise", None])
        mock_audio.return_value = audio_mock
        label, conf = classify_audio_live()
        self.assertIsInstance(label, str)
        self.assertIsInstance(conf, float)

    # -----------------------------
    # Webcam/Attention-Only Edge Cases
    # -----------------------------
    @patch("core.tracker.webcam_pipeline")
    def test_attention_only(self, mock_webcam):
        global _latest_attention
        _latest_attention = random.randint(0, 5)
        frame = mock_webcam.return_value
        # Just logging
        log_multi_modal(
            window="attention_test",
            ocr_keywords={},
            audio_label="none",
            attention_score=_latest_attention,
            interaction_rate=0,
            intent_label="none",
            intent_confidence=0,
            memory_score=0
        )
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM multi_modal_logs")
        self.assertEqual(c.fetchone()[0], 1)
        conn.close()

    # -----------------------------
    # Interaction Rate-Only Edge Cases
    # -----------------------------
    def test_interaction_rate_only(self):
        interaction_rate = random.randint(0, 50)
        intent_data = predict_intent_live(_latest_ocr, "none", _latest_attention, interaction_rate)
        self.assertIn("intent_label", intent_data)
        self.assertIn("confidence", intent_data)

    # -----------------------------
    # Notifications Only
    # -----------------------------
    @patch("core.tracker.notification.notify")
    def test_notifications_only(self, mock_notify):
        concepts = ["test1", "test2", "test3"]
        for c in concepts:
            maybe_notify(c, memory_score=random.random(), graph=get_graph())
        self.assertGreater(mock_notify.call_count, 0)


if __name__ == "__main__":
    unittest.main()
