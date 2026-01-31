# tests/test_input_independence.py
import unittest
from unittest.mock import patch
import random
from core.tracker import maybe_notify, get_graph
from core.audio_module import process_audio
from core.ocr_module import process_ocr
from core.attention_module import process_attention
from core.interaction_module import process_interaction

class TestInputIndependence(unittest.TestCase):
    
    def setUp(self):
        """Reset knowledge graph before each test."""
        self.graph = get_graph()  # Load fresh graph

    # -----------------------------
    # AUDIO INPUT TESTS
    # -----------------------------
    def test_audio_only(self):
        audio_data = [0.1, 0.5, 0.3]  # Example numeric input
        with patch('core.ocr_module.process_ocr'), \
             patch('core.attention_module.process_attention'), \
             patch('core.interaction_module.process_interaction'):
            result = process_audio(audio_data, self.graph)
            self.assertIsNotNone(result)  # Should return processed features

    # -----------------------------
    # OCR INPUT TESTS
    # -----------------------------
    def test_ocr_only(self):
        ocr_input = "Sample text"
        with patch('core.audio_module.process_audio'), \
             patch('core.attention_module.process_attention'), \
             patch('core.interaction_module.process_interaction'):
            nodes_added = process_ocr(ocr_input, self.graph)
            for node in nodes_added:
                self.assertIn("memory_score", self.graph.nodes[node])

    # -----------------------------
    # ATTENTION INPUT TESTS
    # -----------------------------
    def test_attention_only(self):
        attention_score = 0.85
        with patch('core.audio_module.process_audio'), \
             patch('core.ocr_module.process_ocr'), \
             patch('core.interaction_module.process_interaction'):
            self.assertTrue(process_attention(attention_score, self.graph))

    # -----------------------------
    # INTERACTION INPUT TESTS
    # -----------------------------
    def test_interaction_only(self):
        interaction_count = 5
        with patch('core.audio_module.process_audio'), \
             patch('core.ocr_module.process_ocr'), \
             patch('core.attention_module.process_attention'):
            self.assertTrue(process_interaction(interaction_count, self.graph))

    # -----------------------------
    # NOTIFICATIONS (GRAPH SAFE)
    # -----------------------------
    def test_notifications_only(self):
        concept = "independent_test"
        self.graph.add_node(concept)  # Ensure it exists
        with patch('core.audio_module.process_audio'), \
             patch('core.ocr_module.process_ocr'), \
             patch('core.attention_module.process_attention'), \
             patch('core.interaction_module.process_interaction'):
            maybe_notify(concept, memory_score=random.random(), graph=self.graph)
            self.assertIn(concept, self.graph.nodes)

if __name__ == "__main__":
    unittest.main(verbosity=2)
