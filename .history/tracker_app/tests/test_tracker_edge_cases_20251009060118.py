# tests/test_tracker_webcam_off_stress.py
import unittest
from core.tracker import track_loop, get_latest_ocr, get_latest_attention
from core.audio_module import AudioInput
from time import sleep

class TestTrackerWebcamOffStress(unittest.TestCase):

    def setUp(self):
        # Initialize tracker with webcam off
        self.tracker = Tracker(webcam_enabled=False)
        self.tracker.attention = None  # attention should be None when webcam is off

    def simulate_cycle(self, audio_input, interaction_count):
        """
        Simulate a single tracker cycle with given audio and interactions.
        """
        self.tracker.update_attention()  # Should remain None
        self.tracker.process_audio(audio_input)
        self.tracker.update_interactions(interaction_count)
        self.tracker.compute_memory_score()
        self.tracker.send_reminders_if_needed()

    def test_webcam_off_stress(self):
        """
        Simulate multiple cycles with different combinations:
        - Audio: silent / noisy / valid
        - Interactions: 0 / high
        - Memory low triggers notifications
        """
        test_audio_cases = [
            AudioInput(silent=True),
            AudioInput(noisy=True),
            AudioInput(valid=True)
        ]
        test_interactions = [0, 5, 20]  # idle, low, high

        # Run multiple cycles to stress notifications and memory handling
        for i in range(5):  # repeat 5 cycles
            for audio in test_audio_cases:
                for interaction in test_interactions:
                    with self.subTest(cycle=i, audio=audio, interaction=interaction):
                        self.simulate_cycle(audio, interaction)
                        # Assertions
                        self.assertIsNone(self.tracker.attention, "Attention should remain None when webcam off")
                        self.assertTrue(self.tracker.last_intent in ["unknown", "idle", "passive", "studying"],
                                        f"Intent fallback expected, got {self.tracker.last_intent}")
                        # Memory reminder checks
                        if self.tracker.memory_score < 0.5:
                            self.assertIn("memory_low", self.tracker.reminder_log[-1],
                                          "Low memory should trigger reminder")

if __name__ == "__main__":
    unittest.main(verbosity=2)
