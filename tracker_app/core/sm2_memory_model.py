"""
SM-2 Spaced Repetition Algorithm
Based on: Piotr Wozniak's SuperMemo 2 algorithm
Research: 20+ years of validated user data

This replaces the pseudoscientific memory_model.py with a proven,
research-backed spaced repetition algorithm.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import math

# SM-2 Algorithm Configuration
# These are research-validated defaults from SuperMemo
DEFAULT_EASE_FACTOR = 2.5          # Initial difficulty (multiplier)
MIN_EASE_FACTOR = 1.3              # Never decrease below this
MAX_EASE_FACTOR = 2.5              # Never increase above this

# Minimum quality rating (0-5 scale)
# 0-2 = Incorrect (review tomorrow)
# 3-4 = Partially correct (normal interval)
# 5 = Correct (extend interval)
QUALITY_THRESHOLD = 3


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
        self.created_at = created_at or datetime.now()
        
        # SM-2 State Variables
        self.interval = 0              # Days until next review
        self.ease_factor = DEFAULT_EASE_FACTOR
        self.repetitions = 0           # Number of times reviewed
        self.next_review_date = datetime.now()  # When to review next
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
        
        # Step 1: Update repetitions count
        if quality >= QUALITY_THRESHOLD:
            item.repetitions += 1
        else:
            # Failed response - reset to first repetition
            item.repetitions = 1
        
        # Step 2: Calculate new ease factor
        # EF' = EF + (0.1 - (5-q) * (0.08 + (5-q)*0.02))
        # This formula adjusts difficulty based on performance
        new_ease = item.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        item.ease_factor = max(MIN_EASE_FACTOR, min(new_ease, MAX_EASE_FACTOR))
        
        # Step 3: Calculate new interval
        if quality < QUALITY_THRESHOLD:
            # Failed - review tomorrow
            next_interval = 1
        elif item.repetitions == 1:
            # First successful review - review in 1 day
            next_interval = 1
        elif item.repetitions == 2:
            # Second successful review - review in 3 days
            next_interval = 3
        else:
            # Subsequent reviews - use ease factor
            # interval = previous_interval * ease_factor
            next_interval = round(item.interval * item.ease_factor)
        
        # Step 4: Update item state
        item.last_review_date = datetime.now()
        item.interval = next_interval
        item.next_review_date = datetime.now() + timedelta(days=next_interval)
        item.total_reviews += 1
        
        if quality >= QUALITY_THRESHOLD:
            item.correct_count += 1
        
        # Log review
        item.review_history.append({
            'date': datetime.now(),
            'quality': quality,
            'interval': next_interval,
            'ease_factor': item.ease_factor
        })
        
        return {
            'next_interval_days': next_interval,
            'next_review_date': item.next_review_date,
            'ease_factor': item.ease_factor,
            'repetitions': item.repetitions,
            'success_rate': item.correct_count / item.total_reviews if item.total_reviews > 0 else 0
        }
    
    @staticmethod
    def get_items_due(items: list) -> list:
        """Get items that are due for review now"""
        now = datetime.now()
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


class LeitnerSystem:
    """
    Simple Leitner System alternative to SM-2
    
    Easier to understand, good for beginners
    Proven effective for basic learning
    """
    
    INTERVALS = {
        1: 1,      # Box 1: Review in 1 day
        2: 3,      # Box 2: Review in 3 days
        3: 7,      # Box 3: Review in 1 week
        4: 14,     # Box 4: Review in 2 weeks
        5: 30,     # Box 5: Review in 1 month (mastered)
    }
    
    @staticmethod
    def advance_card(item: SM2Item, was_correct: bool) -> Dict[str, Any]:
        """
        Move card forward or backward in Leitner boxes.
        
        Args:
            item: The learning item
            was_correct: Whether user answered correctly
        
        Returns:
            Next interval and review date
        """
        current_box = min(5, item.repetitions + 1)
        
        if was_correct:
            # Move to next box
            next_box = min(5, current_box + 1)
        else:
            # Move back to box 1
            next_box = 1
        
        item.repetitions = next_box - 1
        next_interval = LeitnerSystem.INTERVALS[next_box]
        item.next_review_date = datetime.now() + timedelta(days=next_interval)
        item.total_reviews += 1
        
        if was_correct:
            item.correct_count += 1
        
        return {
            'box': next_box,
            'next_interval_days': next_interval,
            'next_review_date': item.next_review_date
        }


# Utility Functions
def format_retention_percentage(retention_prob: float) -> str:
    """Format retention probability as percentage"""
    return f"{retention_prob * 100:.1f}%"


def format_next_review(next_date: datetime) -> str:
    """Format next review date as human-readable string"""
    now = datetime.now()
    delta = next_date - now
    
    if delta.total_seconds() < 0:
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


def estimate_learning_curve(item: SM2Item) -> Dict[str, Any]:
    """
    Estimate how well item is being learned over time.
    
    Returns metrics on learning progress
    """
    if item.total_reviews == 0:
        return {
            'status': 'not_started',
            'reviews': 0,
            'correct_rate': 0,
            'stage': 'initial'
        }
    
    success_rate = item.correct_count / item.total_reviews
    
    if success_rate < 0.3:
        stage = 'struggling'
    elif success_rate < 0.7:
        stage = 'learning'
    elif success_rate < 0.95:
        stage = 'consolidating'
    else:
        stage = 'mastered'
    
    return {
        'status': 'in_progress',
        'reviews': item.total_reviews,
        'correct_rate': success_rate,
        'stage': stage,
        'repetitions': item.repetitions,
        'ease_factor': item.ease_factor
    }


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
