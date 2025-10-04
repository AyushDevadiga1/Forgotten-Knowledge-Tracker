import numpy as np
from datetime import datetime, timedelta

# Example threshold for reminder
MEMORY_THRESHOLD = 0.6  # below this, schedule review

def compute_memory_score(last_review_time, lambda_val, intent_conf=1.0, attention_score=50, audio_conf=1.0):
    """
    Compute memory score using Ebbinghaus forgetting curve weighted by multi-modal signals
    """
    t = (datetime.now() - last_review_time).total_seconds() / 3600  # time in hours
    R_t = np.exp(-lambda_val * t)  # basic Ebbinghaus curve

    # Normalize attention_score (0-100) to 0-1
    att_factor = attention_score / 100

    # Weighted memory
    memory_score = R_t * intent_conf * att_factor * audio_conf
    return memory_score

def schedule_next_review(last_review_time, memory_score, lambda_val, hours_min=1):
    """
    Compute next review time based on memory score
    """
    if memory_score < MEMORY_THRESHOLD:
        # Simple adaptive logic: sooner if memory is low
        next_review = datetime.now() + timedelta(hours=hours_min)
    else:
        # Longer interval if memory is high
        next_review = last_review_time + timedelta(hours=1/lambda_val)
    return next_review

# Example usage
if __name__ == "__main__":
    last_review = datetime.now() - timedelta(hours=5)  # last reviewed 5 hours ago
    memory_score = compute_memory_score(last_review, lambda_val=0.1, intent_conf=0.9, attention_score=80, audio_conf=1.0)
    next_review = schedule_next_review(last_review, memory_score, lambda_val=0.1)
    print(f"Memory Score: {memory_score:.2f}")z
    print(f"Next Review: {next_review}")
