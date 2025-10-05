# core/memory_model.py
import numpy as np
from datetime import datetime, timedelta
import sqlite3
import math
from config import DB_PATH

# -----------------------------
# Threshold for reminders
# -----------------------------
MEMORY_THRESHOLD = 0.6  # below this, schedule review

# -----------------------------
# Compute weighted memory score
# -----------------------------
def compute_memory_score(
    last_review_time: datetime,
    lambda_val: float,
    intent_conf: float = 1.0,
    attention_score: float = 50,
    audio_conf: float = 1.0
) -> float:
    """
    Compute memory score using Ebbinghaus forgetting curve weighted by multi-modal signals.
    """
    try:
        t = (datetime.now() - last_review_time).total_seconds() / 3600  # time in hours
        R_t = np.exp(-lambda_val * t)  # basic Ebbinghaus curve

        # Normalize attention_score (0-100) to 0-1
        att_factor = max(0.0, min(attention_score / 100.0, 1.0))
        audio_factor = max(0.0, min(audio_conf, 1.0))

        # Weighted memory score
        memory_score = R_t * intent_conf * att_factor * audio_factor
        return max(0.0, min(memory_score, 1.0))  # clamp between 0 and 1
    except Exception as e:
        print(f"[MemoryModel] Error computing memory score: {e}")
        return 0.0

# -----------------------------
# Schedule next review
# -----------------------------
def schedule_next_review(
    last_review_time: datetime,
    memory_score: float,
    lambda_val: float,
    hours_min: float = 1.0
) -> datetime:
    """
    Compute next review time based on memory score.
    """
    try:
        if memory_score < MEMORY_THRESHOLD:
            # Sooner review if memory is low
            next_review = datetime.now() + timedelta(hours=hours_min)
        else:
            # Longer interval if memory is high
            next_review = last_review_time + timedelta(hours=1/lambda_val)
        return next_review
    except Exception as e:
        print(f"[MemoryModel] Error scheduling next review: {e}")
        return datetime.now() + timedelta(hours=1)

# -----------------------------
# Ebbinghaus forgetting curve
# -----------------------------
def forgetting_curve(t_hours: float, s: float = 1.25) -> float:
    """
    Compute probability of recall using Ebbinghaus forgetting curve.
    """
    try:
        return math.exp(-t_hours / s)
    except Exception as e:
        print(f"[MemoryModel] Error in forgetting_curve: {e}")
        return 0.0

# -----------------------------
# Log forgetting curve to DB
# -----------------------------
def log_forgetting_curve(
    concept: str,
    last_seen_time: datetime,
    observed_usage: int = 1,
    memory_strength: float = 1.25
) -> float:
    """
    Compute predicted recall and log it into memory_decay table.

    Returns predicted recall.
    """
    try:
        # Calculate hours since last review
        t_hours = (datetime.now() - last_seen_time).total_seconds() / 3600
        predicted_recall = forgetting_curve(t_hours, memory_strength)

        # Insert into DB
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO memory_decay (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            concept,
            last_seen_time.strftime("%Y-%m-%d %H:%M:%S"),
            predicted_recall,
            observed_usage,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()

        return predicted_recall
    except Exception as e:
        print(f"[MemoryModel] Error logging forgetting curve: {e}")
        return 0.0

# -----------------------------
# Test / Demo
# -----------------------------
if __name__ == "__main__":
    last_review = datetime.now() - timedelta(hours=5)  # last reviewed 5 hours ago
    memory_score = compute_memory_score(
        last_review, lambda_val=0.1, intent_conf=0.9, attention_score=80, audio_conf=1.0
    )
    next_review = schedule_next_review(last_review, memory_score, lambda_val=0.1)

    predicted_recall = log_forgetting_curve("Photosynthesis", last_review, observed_usage=2)

    print(f"Memory Score: {memory_score:.2f}")
    print(f"Next Review: {next_review}")
    print(f"Predicted Recall (logged): {predicted_recall:.2f}")
