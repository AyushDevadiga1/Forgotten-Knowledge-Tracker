# tests/test_tracker_edge_cases.py
import unittest
from threading import Event, Thread
import time

from core.tracker import track_loop, get_latest_ocr, get_latest_attention

class TestTrackerEdgeCases(unittest.TestCase):

    def setUp(self):
        # Create a stop event to control the tracker loop
        self.stop_event = Event()
        # Run the tracker loop in a separate thread so it doesn't block
        self.tracker_thread = Thread(target=track_loop, args=(self.stop_event,))
        self.tracker_thread.start()
        # Let it run a short while to collect some data
        time.sleep(2)
        # Stop the tracker loop
        self.stop_event.set()
        self.tracker_thread.join()

    def test_latest_ocr(self):
        ocr = get_latest_ocr()
        self.assertIsInstance(ocr, dict)
        # You can add more checks depending on expected keys
        for k, v in ocr.items():
            self.assertIn("score", v)
            self.assertIn("count", v)

    def test_latest_attention(self):
        attention = get_latest_attention()
        # Can be None if webcam off
        self.assertTrue(attention is None or isinstance(attention, int))

if __name__ == "__main__":
    unittest.main(verbosity=2)
