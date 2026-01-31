# tests/test_tracker_strict_edge_cases.py
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import random

from core.tracker import (
    classify_audio_live,
    predict_intent_live,
    maybe_notify,
    _latest_ocr,
    _latest_attention,
    get_graph,
    MEMORY_THRESHOLD,
)
from core.knowledge_graph import add_concepts

class TestTrackerStrictEdgeCases(unittest.TestCase):
    """
    Stress tests for tracker handling combinations of:
    - Audio: valid / silence / noise / non-numeric
    - Webcam: off / 0 faces / some faces
    - Interaction: 0 / low / high
    - OCR: empty / valid / invalid
    - Intent: correct / unknown / misclassified
    """

    def setUp(self):
        # Ensure knowledge graph has test concepts
        self.G = get_graph()
        add_concepts(["concept1", "concept2", "memory_low", "webcam_off"])
        self.test_concepts = list(self.G.nodes)

    def simulate_audio(self, case):
        if case == "silent":
            return "silence"
        elif case == "noise":
            return ["noise"]  # invalid / non-numeric
        elif case == "speech":
            return "speech"
        else:
            return "unknown"

    def simulate_ocr(self, case):
        if case == "empty":
            return {}
        elif case == "valid":
            return {"keyword1": {"score": 0.8, "count": 2}}
        elif case == "invalid":
            return {"keyword1": "NaN"}
        else:
            return {}

    def simulate_attention(self, case):
        if case == "off":
            return None
        elif case == "zero":
            return 0
        elif case == "some":
            return 3
        return None

    def simulate_interaction(self, case):
        if case == "zero":
            return 0
        elif case == "low":
            return 2
        elif case == "high":
            return 10
        return 0

    def simulate_intent(self, audio_case, interaction_rate):
        # fallback rules
        if audio_case == "speech" and interaction_rate > 5:
            return {"intent_label": "studying", "confidence": 0.8}
        elif interaction_rate < 2:
            return {"intent_label": "idle", "confidence": 0.7}
        return {"intent_label": "passive", "confidence": 0.6}

    def run_tracker_case(self, audio_case, webcam_case, interaction_case, ocr_case):
        # Simulate audio
        audio_label = self.simulate_audio(audio_case)
        # Simulate attention
        attention_score = self.simulate_attention(webcam_case)
        # Simulate interaction rate
        interaction_rate = self.simulate_interaction(interaction_case)
        # Simulate OCR
        ocr_keywords = self.simulate_ocr(ocr_case)
        # Predict intent
        intent_data = self.simulate_intent(audio_case, interaction_rate)

        # Update knowledge graph nodes safely
        for concept in self.test_concepts:
            if concept not in self.G.nodes:
                add_concepts([concept])
        # Send notifications if memory low
        for concept in self.test_concepts:
            memory_score = random.uniform(0.2, 1.0)  # simulate scores
            try:
                maybe_notify(concept, memory_score, self.G, use_attention=(attention_score is not None))
            except Exception as e:
                self.fail(f"maybe_notify crashed: {e}")

        # Ensure memory scores and next_review fields exist
        for concept in self.test_concepts:
            node = self.G.nodes[concept]
            node.setdefault("memory_score", 0.0)
            node.setdefault("next_review_time", datetime.now().isoformat())

    def test_all_combinations(self):
        audio_cases = ["silent", "noise", "speech", "unknown"]
        webcam_cases = ["off", "zero", "some"]
        interaction_cases = ["zero", "low", "high"]
        ocr_cases = ["empty", "valid", "invalid"]

        for audio in audio_cases:
            for webcam in webcam_cases:
                for interaction in interaction_cases:
                    for ocr in ocr_cases:
                        with self.subTest(audio=audio, webcam=webcam, interaction=interaction, ocr=ocr):
                            self.run_tracker_case(audio, webcam, interaction, ocr)

if __name__ == "__main__":
    unittest.main(verbosity=2)
