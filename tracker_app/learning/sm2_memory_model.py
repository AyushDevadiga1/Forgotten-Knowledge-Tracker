"""SM-2 spaced repetition algorithm (Piotr Wozniak's SuperMemo 2).

Research-backed scheduling defaults; complements the AWFC retention model.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import math

from tracker_app.utils import utcnow as _utcnow

# SM-2 Algorithm Configuration
# These are research-validated defaults from SuperMemo
DEFAULT_EASE_FACTOR = 2.5          # Initial difficulty (multiplier)
MIN_EASE_FACTOR = 1.3              # Never decrease below this
MAX_EASE_FACTOR = 3.5              # Never increase above this

# Minimum quality rating (0-5 scale)
# 0-2 = Incorrect (review tomorrow)
# 3-4 = Partially correct (normal interval)
# 5 = Correct (extend interval)
QUALITY_THRESHOLD = 3

# Deliberate choice (Phase 11.6): canonical SM-2 uses 6 days for the second
# successful review; we use a gentler 3-day ramp for first-time learners.
# Shared by sm2_memory_model.py and concept_scheduler.py so both subsystems
# implement the same schedule.
SECOND_REVIEW_INTERVAL_DAYS = 3


class SM2Item:
    """Single item in spaced repetition system"""
    
    def __init__(
        self,
        item_id: str,
        question: str,
        answer: str,
        difficulty: str = "medium",  # easy, medium, hard
        created_at: datetime = None
    ):
        """
        Args:
            item_id: Unique identifier
            question: What to learn
            answer: The answer/explanation
            difficulty: Initial difficulty assessment
            created_at: When item was created
        """
        self.item_id = item_id
        self.question = question
        self.answer = answer
        self.difficulty = difficulty
        self.created_at = created_at or _utcnow()
        
        # SM-2 State Variables
        self.interval = 0              # Days until next review
        self.ease_factor = DEFAULT_EASE_FACTOR
        self.repetitions = 0           # Number of times reviewed
        self.next_review_date = _utcnow()  # When to review next
        self.last_review_date = None   # Last review timestamp
        
        # Statistics
        self.review_history = []       # [(date, quality_rating), ...]
        self.correct_count = 0         # Number of correct responses
        self.total_reviews = 0         # Total review attempts


class SM2Scheduler:
    """
    SM-2 Spaced Repetition Scheduler
    
    Based on Ebbinghaus forgetting curve + SuperMemo research
    """
    
    @staticmethod
    def calculate_next_interval(
        item: SM2Item,
        quality: int  # 0-5 scale
    ) -> Dict[str, Any]:
        """
        Calculate next review interval based on user response quality.
        
        Quality Scale (0-5):
        0 = Complete blackout, couldn't recall at all
        1 = Incorrect, only vague recollection
        2 = Incorrect, but seemed familiar
        3 = Correct response after some effort
        4 = Correct response with some hesitation
        5 = Perfect response, immediate recall
        
        Returns:
            {
                'next_interval_days': int,
                'next_review_date': datetime,
                'ease_factor': float,
                'repetitions': int
            }
        """
        if not (0 <= quality <= 5):
            raise ValueError("Quality must be between 0 and 5")
        
        # Use the shared SM-2 calculation (single source of truth)
        sm2_result = calculate_sm2_interval(
            interval=item.interval,
            ease_factor=item.ease_factor,
            repetitions=item.repetitions,
            quality=quality,
        )
        
        item.ease_factor = sm2_result['ease_factor']
        item.repetitions = sm2_result['repetitions']
        item.interval = sm2_result['interval']
        
        # Step 4: Update item state (single utcnow() call)
        now = _utcnow()
        item.last_review_date = now
        item.next_review_date = now + timedelta(days=item.interval)
        item.total_reviews += 1
        
        if quality >= QUALITY_THRESHOLD:
            item.correct_count += 1
        
        # Log review
        item.review_history.append({
            'date': now,
            'quality': quality,
            'interval': item.interval,
            'ease_factor': item.ease_factor
        })
        
        return {
            'next_interval_days': item.interval,
            'next_review_date': item.next_review_date,
            'ease_factor': item.ease_factor,
            'repetitions': item.repetitions,
            'success_rate': item.correct_count / item.total_reviews if item.total_reviews > 0 else 0
        }
    
    @staticmethod
    def get_items_due(items: list) -> list:
        """Get items that are due for review now"""
        now = _utcnow()
        return [item for item in items if item.next_review_date <= now]
    
    @staticmethod
    def estimate_retention(item: SM2Item) -> Dict[str, float]:
        """
        Estimate probability of recalling this item at future times.
        
        Uses: R(t) = e^(-t/S)
        where t = time in days, S = strength (based on repetitions)
        
        Returns probability estimates for 1, 7, 30, 365 days
        """
        if item.last_review_date is None:
            return {
                'now': 0.0,
                '1_day': 0.0,
                '7_days': 0.0,
                '30_days': 0.0,
                '365_days': 0.0
            }
        
        # Strength increases with repetitions
        # S = 1 + (repetitions * 0.1)
        strength = 1.0 + (item.repetitions * 0.1)
        
        def retention_probability(days: int) -> float:
            """Calculate P(recall) after given days"""
            return math.exp(-days / strength)
        
        return {
            'now': min(1.0, retention_probability(0)),
            '1_day': retention_probability(1),
            '7_days': retention_probability(7),
            '30_days': retention_probability(30),
            '365_days': retention_probability(365)
        }




def calculate_sm2_interval(
    interval: int,
    ease_factor: float,
    repetitions: int,
    quality: int,
) -> dict:
    """Pure SM-2 interval calculation shared by SM2Item and TrackedConcept.

    Works with raw values instead of ORM models, so both
    SM2Scheduler.calculate_next_interval() and ConceptScheduler.schedule_next_review()
    use the exact same logic.

    Args:
        interval: current interval in days
        ease_factor: current ease factor
        repetitions: current repetition count
        quality: review quality 0-5

    Returns:
        dict with keys: interval, ease_factor, repetitions
    """
    if not (0 <= quality <= 5):
        raise ValueError("Quality must be between 0 and 5")

    # Ease factor adjustment (canonical SM-2 formula)
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ease = max(MIN_EASE_FACTOR, min(ease_factor + delta, MAX_EASE_FACTOR))

    if quality < QUALITY_THRESHOLD:
        new_reps = 1
        new_interval = 1
    else:
        new_reps = repetitions + 1
        if new_reps == 1:
            new_interval = 1
        elif new_reps == 2:
            new_interval = SECOND_REVIEW_INTERVAL_DAYS
        else:
            new_interval = max(1, round(interval * new_ease))

    return {
        'interval': new_interval,
        'ease_factor': new_ease,
        'repetitions': new_reps,
    }


def format_next_review(next_date: datetime) -> str:
    """Format next review date as human-readable string"""
    now = _utcnow()
    delta = next_date - now
    
    if delta.total_seconds() <= 0:
        return "NOW"
    elif delta.days == 0:
        hours = delta.seconds // 3600
        return f"in {hours} hours"
    elif delta.days == 1:
        return "tomorrow"
    elif delta.days < 7:
        return f"in {delta.days} days"
    elif delta.days < 30:
        weeks = delta.days // 7
        return f"in {weeks} week{'s' if weeks > 1 else ''}"
    else:
        months = delta.days // 30
        return f"in {months} month{'s' if months > 1 else ''}"


# Example usage
if __name__ == "__main__":
    # Create a sample item
    item = SM2Item(
        item_id="py_001",
        question="What is a list comprehension in Python?",
        answer="A concise way to create lists: [x*2 for x in range(5)]"
    )
    
    print("=== SM-2 Spaced Repetition Example ===\n")
    
    # Simulate reviews
    reviews = [5, 4, 5, 4, 5]  # Quality ratings
    
    for i, quality in enumerate(reviews, 1):
        result = SM2Scheduler.calculate_next_interval(item, quality)
        retention = SM2Scheduler.estimate_retention(item)
        
        print(f"Review {i}: Quality={quality}")
        print(f"  Next interval: {result['next_interval_days']} days")
        print(f"  Ease factor: {result['ease_factor']:.2f}")
        print(f"  Success rate: {result['success_rate']:.1%}")
        print(f"  Predicted recall in 7 days: {retention['7_days']:.1%}")
        print()

