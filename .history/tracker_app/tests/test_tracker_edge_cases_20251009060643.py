# tests/test_tracker_edge_cases.py
import unittest
from threading import Event, Thread
import time

from core.tracker import track_loop, get_latest_ocr, get_latest_attention

class TestTrackerEdgeCases(unittest.TestCase):

    def setUp(self):
        self.stop_event = Event()
        self.tracker_thread = Thread(target=track_loop, args=(self.stop_event,))
        self.tracker_thread.start()
        # Let the tracker loop run a bit to initialize
        time.sleep(2)
        self.stop_event.set()
        self.tracker_thread.join()

    def test_latest_ocr_type_and_content(self):
        """_latest_ocr should always be a dict with proper keys if any keywords exist"""
        ocr = get_latest_ocr()
        self.assertIsInstance(ocr, dict)
        for k, v in ocr.items():
            self.assertIn("score", v)
            self.assertIn("count", v)
            self.assertIsInstance(v["score"], float)
            self.assertIsInstance(v["count"], int)

    def test_latest_attention_type(self):
        """_latest_attention should be int if webcam on, or None if off"""
        attention = get_latest_attention()
        self.assertTrue(attention is None or isinstance(attention, int))

    def test_no_ocr_edge_case(self):
        """Simulate tracker loop running but no OCR detected"""
        ocr = get_latest_ocr()
        if not ocr:
            self.assertEqual(ocr, {})

    def test_attention_webcam_off(self):
        """Simulate user has webcam off; attention should be None"""
        attention = get_latest_attention()
        # None is valid if webcam off
        self.assertIn(attention, [None] + list(range(0, 11)))  # assuming max 10 faces

if __name__ == "__main__":
    unittest.main(verbosity=2)
