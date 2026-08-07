"""
Tests: micro-quiz trigger thresholds + gating (Phase 10).

- IDLE_CYCLES_REQUIRED is 12 (~60 s at 5 s cadence), not the old 3.
- should_show_quiz never fires outside an active study session.
- Attention signal and cooldown still gate correctly.

Run: python -m pytest tracker_app/tests/test_quiz_trigger.py -v
"""

import unittest
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tracker_app.tracking import quiz_engine


class TestQuizTrigger(unittest.TestCase):
    def setUp(self):
        quiz_engine._last_quiz_time = None

    def test_below_threshold_never_fires(self):
        for cycles in range(0, quiz_engine.IDLE_CYCLES_REQUIRED):
            self.assertFalse(
                quiz_engine.should_show_quiz(cycles, False, 0.0))

    def test_at_threshold_fires(self):
        self.assertTrue(
            quiz_engine.should_show_quiz(
                quiz_engine.IDLE_CYCLES_REQUIRED, False, 0.0))

    def test_beyond_threshold_fires(self):
        self.assertTrue(
            quiz_engine.should_show_quiz(
                quiz_engine.IDLE_CYCLES_REQUIRED + 8, False, 0.0))

    def test_attention_blocks_when_paying_attention(self):
        self.assertFalse(quiz_engine.should_show_quiz(12, True, 50.0))
        self.assertTrue(quiz_engine.should_show_quiz(12, True, 10.0))

    def test_inactive_session_never_fires(self):
        self.assertFalse(
            quiz_engine.should_show_quiz(12, False, 0.0, session_active=False))
        self.assertFalse(
            quiz_engine.should_show_quiz(12, False, 0.0, session_active=False))
        self.assertTrue(
            quiz_engine.should_show_quiz(12, False, 0.0, session_active=True))

    def test_cooldown_blocks_repeat_quiz(self):
        quiz_engine._last_quiz_time = datetime.utcnow()
        self.assertFalse(quiz_engine.should_show_quiz(12, False, 0.0))

    def test_cooldown_expires(self):
        quiz_engine._last_quiz_time = datetime.utcnow() - timedelta(
            minutes=quiz_engine.QUIZ_COOLDOWN_MINUTES + 1)
        self.assertTrue(quiz_engine.should_show_quiz(12, False, 0.0))

    def test_idle_threshold_is_12_cycles(self):
        # Regression guard: 3 cycles (~15 s) was far too aggressive.
        self.assertEqual(quiz_engine.IDLE_CYCLES_REQUIRED, 12)


if __name__ == '__main__':
    unittest.main()
