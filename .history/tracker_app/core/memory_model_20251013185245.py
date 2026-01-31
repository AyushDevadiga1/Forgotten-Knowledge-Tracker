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

def safe_parse_datetime(dt_value, default=None):
    """Safely parse datetime from various formats"""
    if default is None:
        default = datetime.now()
    
    if isinstance(dt_value, datetime):
        return dt_value
    elif isinstance(dt_value, str):
        try:
            return datetime.fromisoformat(dt_value)
        except (ValueError, TypeError):
            try:
                return datetime.strptime(dt_value, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                return default
    else:
        return default

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
        # Ensure last_review_time is a datetime object
        last_review = safe_parse_datetime(last_review_time, datetime.now())
        
        # Time in hours since last review
        t_hours = max(0, (datetime.now() - last_review).total_seconds() / 3600)
        
        # Ebbinghaus forgetting curve: R = exp(-λt)
        R_t = np.exp(-lambda_val * t_hours)

        # Normalize and weight multi-modal factors
        att_factor = max(0.1, min(attention_score / 100.0, 1.0))  # Minimum 0.1 to avoid zeroing out
        intent_factor = max(0.3, min(intent_conf, 1.0))  # Intent confidence factor
        audio_factor = max(0.5, min(audio_conf, 1.0))  # Audio presence factor

        # Combined modality factor (geometric mean for balanced weighting)
        modality_factor = (att_factor * intent_factor * audio_factor) ** (1/3)

        # Final memory score
        memory_score = R_t * modality_factor
        
        return max(0.1, min(memory_score, 1.0))  # clamp between 0.1 and 1.0
        
    except Exception as e:
        print(f"[MemoryModel] Error computing memory score: {e}")
        return 0.3  # Default fallback

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
    Compute next review time based on memory score using spaced repetition principles.
    """
    try:
        last_review = safe_parse_datetime(last_review_time, datetime.now())
        
        if memory_score < MEMORY_THRESHOLD:
            # Review soon if memory is weak
            interval_hours = hours_min
        else:
            # Optimized interval based on memory strength
            # Stronger memory = longer interval (exponential scaling)
            base_interval = 1.0 / max(0.01, lambda_val)  # Base interval from decay rate
            strength_factor = memory_score ** 2  # Square to favor high scores
            interval_hours = max(hours_min, base_interval * strength_factor)
            
            # Cap maximum interval to 30 days for practicality
            interval_hours = min(interval_hours, 24 * 30)
        
        next_review = datetime.now() + timedelta(hours=interval_hours)
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
    s: memory strength parameter (higher = slower decay)
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
        last_seen = safe_parse_datetime(last_seen_time, datetime.now())
        
        # Calculate hours since last review
        t_hours = max(0, (datetime.now() - last_seen).total_seconds() / 3600)
        predicted_recall = forgetting_curve(t_hours, memory_strength)

        # Insert into DB
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO memory_decay (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            str(concept),
            last_seen.strftime("%Y-%m-%d %H:%M:%S"),
            float(predicted_recall),
            int(observed_usage),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()

        return predicted_recall
        
    except Exception as e:
        print(f"[MemoryModel] Error logging forgetting curve: {e}")
        return 0.0

# -----------------------------
# Get memory statistics for a concept
# -----------------------------
def get_concept_memory_stats(concept: str):
    """Get memory statistics for a specific concept"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''
            SELECT last_seen_ts, predicted_recall, observed_usage 
            FROM memory_decay 
            WHERE keyword = ? 
            ORDER BY last_seen_ts DESC 
            LIMIT 10
        ''', (str(concept),))
        
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            return None
            
        # Convert to structured data
        stats = {
            'last_seen': safe_parse_datetime(rows[0][0]),
            'current_recall': float(rows[0][1]),
            'usage_count': int(rows[0][2]),
            'history': []
        }
        
        for row in rows:
            stats['history'].append({
                'timestamp': safe_parse_datetime(row[0]),
                'recall': float(row[1]),
                'usage': int(row[2])
            })
            
        return stats
        
    except Exception as e:
        print(f"[MemoryModel] Error getting concept stats: {e}")
        return None

# -----------------------------
# Test / Demo
# -----------------------------
if __name__ == "__main__":
    last_review = datetime.now() - timedelta(hours=5)
    memory_score = compute_memory_score(
        last_review, lambda_val=0.1, intent_conf=0.9, attention_score=80, audio_conf=1.0
    )
    next_review = schedule_next_review(last_review, memory_score, lambda_val=0.1)

    predicted_recall = log_forgetting_curve("Photosynthesis", last_review, observed_usage=2)

    print(f"Memory Score: {memory_score:.2f}")
    print(f"Next Review: {next_review}")
    print(f"Predicted Recall (logged): {predicted_recall:.2f}")
    
    # Test concept stats
    stats = get_concept_memory_stats("Photosynthesis")
    if stats:
        print(f"Concept Stats: {stats}")