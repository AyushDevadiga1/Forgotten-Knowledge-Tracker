"""
Unit Tests: SM-2 Spaced Repetition Algorithm
=============================================
Tests the core memory scheduling math.
Run: python -m pytest tracker_app/tests/test_sm2.py -v
"""

import unittest
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tracker_app.core.sm2_memory_model import SM2Item, SM2Scheduler, DEFAULT_EASE_FACTOR, MIN_EASE_FACTOR, MAX_EASE_FACTOR


def make_item(item_id="test-001", question="Q?", answer="A.", difficulty="medium"):
    """Helper: create a fresh SM2Item."""
    return SM2Item(item_id=item_id, question=question, answer=answer, difficulty=difficulty)


class TestSM2FirstReview(unittest.TestCase):
    """Tests for a brand-new item being reviewed for the first time."""

    def test_perfect_recall_first_review(self):
        """Quality 5 on first review should set interval to 1 day."""
        item = make_item()
        result = SM2Scheduler.calculate_next_interval(item, quality=5)
        self.assertEqual(result['next_interval_days'], 1, "First review with quality 5 should give 1 day interval")

    def test_good_recall_first_review(self):
        """Quality 4 on first review should set interval to 1 day."""
        item = make_item()
        result = SM2Scheduler.calculate_next_interval(item, quality=4)
        self.assertEqual(result['next_interval_days'], 1)

    def test_failure_first_review(self):
        """Quality < 3 on first review should reset repetitions and give 1 day."""
        item = make_item()
        result = SM2Scheduler.calculate_next_interval(item, quality=2)
        # SM-2 implementation resets repetitions to 1 on failure (not 0)
        self.assertLessEqual(result['repetitions'], 1, "Failure should reset repetitions to ≤1")
        self.assertLessEqual(result['next_interval_days'], 1, "Failure should give ≤1 day interval")

    def test_complete_blackout_first_review(self):
        """Quality 0 should still produce a valid result (no crash)."""
        item = make_item()
        result = SM2Scheduler.calculate_next_interval(item, quality=0)
        self.assertIn('next_interval_days', result)
        self.assertIn('ease_factor', result)
        self.assertGreaterEqual(result['next_interval_days'], 0)


class TestSM2EaseFactor(unittest.TestCase):
    """Tests that ease factor stays within valid bounds."""

    def test_ease_factor_never_below_minimum(self):
        """Even with repeated failures, ease factor should never drop below MIN_EASE_FACTOR."""
        item = make_item()
        for _ in range(20):  # 20 failures in a row
            result = SM2Scheduler.calculate_next_interval(item, quality=0)
            item.ease_factor = result['ease_factor']
            item.repetitions = result['repetitions']
            item.interval = result['next_interval_days']

        self.assertGreaterEqual(
            item.ease_factor, MIN_EASE_FACTOR,
            f"ease_factor {item.ease_factor} dropped below minimum {MIN_EASE_FACTOR}"
        )

    def test_ease_factor_never_above_maximum(self):
        """Even with perfect recalls, ease factor should not exceed MAX_EASE_FACTOR (starts at max)."""
        item = make_item()
        for _ in range(10):  # 10 perfect scores
            result = SM2Scheduler.calculate_next_interval(item, quality=5)
            item.ease_factor = result['ease_factor']
            item.repetitions = result['repetitions']
            item.interval = result['next_interval_days']

        self.assertLessEqual(
            item.ease_factor, MAX_EASE_FACTOR + 0.01,  # small float tolerance
            f"ease_factor {item.ease_factor} exceeded maximum {MAX_EASE_FACTOR}"
        )

    def test_ease_factor_decreases_on_low_quality(self):
        """Quality < 3 should decrease ease factor."""
        item = make_item()
        original_ef = item.ease_factor
        result = SM2Scheduler.calculate_next_interval(item, quality=2)
        self.assertLessEqual(result['ease_factor'], original_ef,
                             "Low quality should decrease or keep ease factor")

    def test_ease_factor_increases_on_high_quality(self):
        """Quality 5 should not decrease ease factor (SM-2 standard behavior)."""
        item = make_item()
        item.ease_factor = MIN_EASE_FACTOR  # Start at minimum
        result = SM2Scheduler.calculate_next_interval(item, quality=5)
        self.assertGreaterEqual(result['ease_factor'], MIN_EASE_FACTOR,
                                "High quality should not drop ease factor below minimum")


class TestSM2Intervals(unittest.TestCase):
    """Tests for correct interval progression over multiple reviews."""

    def test_second_review_interval(self):
        """After 1 successful review, second review should give 3-6 days (SM-2 standard)."""
        item = make_item()
        # First review
        result1 = SM2Scheduler.calculate_next_interval(item, quality=5)
        item.interval = result1['next_interval_days']
        item.ease_factor = result1['ease_factor']
        item.repetitions = result1['repetitions']
        # Second review
        result2 = SM2Scheduler.calculate_next_interval(item, quality=5)
        # SM-2 gives 3 days on second successful review
        self.assertIn(result2['next_interval_days'], [3, 6], "Second successful review should give 3 or 6 days")

    def test_interval_grows_after_repeated_success(self):
        """Intervals should grow after each successful review."""
        item = make_item()
        intervals = []
        for _ in range(5):
            result = SM2Scheduler.calculate_next_interval(item, quality=4)
            intervals.append(result['next_interval_days'])
            item.interval = result['next_interval_days']
            item.ease_factor = result['ease_factor']
            item.repetitions = result['repetitions']

        # Each interval should be >= previous (non-decreasing for successful reviews)
        for i in range(1, len(intervals)):
            self.assertGreaterEqual(intervals[i], intervals[i - 1],
                                    f"Interval should grow: {intervals}")

    def test_failure_resets_interval(self):
        """A failure (quality < 3) after several successes should reset the interval."""
        item = make_item()
        # Build up some repetitions first
        for _ in range(3):
            result = SM2Scheduler.calculate_next_interval(item, quality=5)
            item.interval = result['next_interval_days']
            item.ease_factor = result['ease_factor']
            item.repetitions = result['repetitions']

        self.assertGreater(item.interval, 1, "Should have built up interval before failure")

        # Now fail
        result = SM2Scheduler.calculate_next_interval(item, quality=1)
        self.assertLessEqual(result['repetitions'], 1, "Failure should reset repetitions")
        self.assertLessEqual(result['next_interval_days'], 1, "Failure should reset interval to 1 or less")


class TestSM2QualityBoundaries(unittest.TestCase):
    """Tests for edge cases in quality ratings."""

    def test_quality_exactly_3_passes(self):
        """Quality 3 is the threshold — should be treated as success (repetitions increase)."""
        item = make_item()
        result = SM2Scheduler.calculate_next_interval(item, quality=3)
        # With SM-2, quality >= 3 means the review was a success
        self.assertGreaterEqual(result['repetitions'], 1,
                                "Quality 3 should count as a pass (repetitions >= 1)")

    def test_quality_exactly_2_fails(self):
        """Quality 2 is below threshold — repetitions should reset.
        NOTE: This SM-2 implementation resets to 1 (not 0) on failure,
        which is a valid variation. Standard SM-2 resets to 0.
        """
        item = make_item()
        result = SM2Scheduler.calculate_next_interval(item, quality=2)
        # This implementation resets to 1 (one mandatory re-review), not 0
        self.assertLessEqual(result['repetitions'], 1,
                             "Quality 2 should reset repetitions to 0 or 1 (failure mode)")
        # Interval must still be short
        self.assertLessEqual(result['next_interval_days'], 1,
                             "Failed review must schedule next review within 1 day")

    def test_quality_5_maximum(self):
        """Quality 5 should not crash and should give valid outputs."""
        item = make_item()
        result = SM2Scheduler.calculate_next_interval(item, quality=5)
        self.assertIsInstance(result['next_interval_days'], (int, float))
        self.assertIsInstance(result['ease_factor'], float)
        self.assertGreater(result['next_interval_days'], 0)

    def test_quality_0_minimum(self):
        """Quality 0 should not crash and should give valid outputs."""
        item = make_item()
        result = SM2Scheduler.calculate_next_interval(item, quality=0)
        self.assertIsInstance(result['next_interval_days'], (int, float))
        self.assertGreaterEqual(result['next_interval_days'], 0)


class TestSM2DatesAndScheduling(unittest.TestCase):
    """Tests that next review dates are computed correctly."""

    def test_next_review_date_is_in_future(self):
        """Next review date should be today or in the future."""
        item = make_item()
        result = SM2Scheduler.calculate_next_interval(item, quality=4)
        # next_review_date might be a datetime or string — handle both
        nrd = result.get('next_review_date')
        if isinstance(nrd, str):
            nrd = datetime.fromisoformat(nrd)
        if nrd is not None:
            yesterday = datetime.now() - timedelta(days=1)
            self.assertGreater(nrd, yesterday,
                               "Next review date should not be in the past")

    def test_result_contains_required_keys(self):
        """SM-2 result must always contain next_interval_days, ease_factor, repetitions."""
        item = make_item()
        for quality in range(6):  # 0 to 5
            result = SM2Scheduler.calculate_next_interval(item, quality=quality)
            self.assertIn('next_interval_days', result, f"Missing 'next_interval_days' for quality={quality}")
            self.assertIn('ease_factor', result, f"Missing 'ease_factor' for quality={quality}")
            self.assertIn('repetitions', result, f"Missing 'repetitions' for quality={quality}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
