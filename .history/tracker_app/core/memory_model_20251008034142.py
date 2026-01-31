"""
Memory Model Module (IEEE-Ready v2, Unified Logging)
---------------------------------------------------
- Computes memory score based on multi-modal signals and Ebbinghaus forgetting curve.
- Schedules next review times adaptively.
- Logs forgetting curve events in the centralized multi_modal_logs table.
"""

import numpy as np
from datetime import datetime, timedelta
import math
import logging
from typing import Optional
from core.db_module import log_multi_modal_event
from config import DB_PATH

# -----------------------------
# LOGGER SETUP
# -----------------------------
logging.basicConfig(
    filename="logs/memory_model.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Ensure logs directory exists
import os
if not os.path.exists("logs"):
    os.makedirs("logs", exist_ok=True)

# -----------------------------
# CONFIGURABLE PARAMETERS
# -----------------------------
MEMORY_THRESHOLD: float = 0.6  # below this, schedule review

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
    Returns value in [0,1].
    """
    try:
        if not isinstance(last_review_time, datetime):
            raise ValueError("last_review_time must be datetime object")
        t_hours = max(0.0, (datetime.now() - last_review_time).total_seconds() / 3600)
        lambda_val = max(0.001, lambda_val)
        R_t = np.exp(-lambda_val * t_hours)
        att_factor = max(0.0, min(attention_score / 100.0, 1.0))
        audio_factor = max(0.0, min(audio_conf, 1.0))
        intent_conf = max(0.0, min(intent_conf, 1.0))
        memory_score = R_t * intent_conf * att_factor * audio_factor
        return max(0.0, min(memory_score, 1.0))
    except Exception as e:
        logging.error(f"[MemoryModel] Error computing memory score: {e}")
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
    Returns datetime object.
    """
    try:
        if memory_score < 0.0 or memory_score > 1.0:
            memory_score = max(0.0, min(memory_score, 1.0))
        if memory_score < MEMORY_THRESHOLD:
            return datetime.now() + timedelta(hours=hours_min)
        lambda_val = max(0.001, lambda_val)
        if not isinstance(last_review_time, datetime):
            last_review_time = datetime.now()
        return last_review_time + timedelta(hours=1/lambda_val)
    except Exception as e:
        logging.error(f"[MemoryModel] Error scheduling next review: {e}")
        return datetime.now() + timedelta(hours=1)

# -----------------------------
# Ebbinghaus forgetting curve
# -----------------------------
def forgetting_curve(t_hours: float, s: float = 1.25) -> float:
    """
    Compute probability of recall using Ebbinghaus forgetting curve.
    Returns value in [0,1].
    """
    try:
        t_hours = max(0.0, t_hours)
        s = max(0.01, s)
        prob = math.exp(-t_hours / s)
        return max(0.0, min(prob, 1.0))
    except Exception as e:
        logging.error(f"[MemoryModel] Error in forgetting_curve: {e}")
        return 0.0

# -----------------------------
# Log forgetting curve via centralized DB logger
# -----------------------------
def log_forgetting_curve(
    concept: str,
    last_seen_time: datetime,
    observed_usage: int = 1,
    memory_strength: float = 1.25
) -> float:
    """
    Compute predicted recall and log it into multi_modal_logs table via centralized logger.
    Returns predicted recall.
    """
    try:
        if not isinstance(last_seen_time, datetime):
            last_seen_time = datetime.now()
        t_hours = max(0.0, (datetime.now() - last_seen_time).total_seconds() / 3600)
        predicted_recall = forgetting_curve(t_hours, memory_strength)

        # Centralized logging
        try:
            log_multi_modal_event(
                window_title=f"ForgettingCurve: {concept}",
                ocr_keywords=concept,
                audio_label=None,
                attention_score=None,
                interaction_rate=None,
                intent_label="memory_decay",
                intent_confidence=None,
                memory_score=predicted_recall,
                source_module="MemoryModel"
            )
        except Exception as log_e:
            logging.error(f"[MemoryModel] Logging failed for '{concept}': {log_e}")

        return max(0.0, min(predicted_recall, 1.0))
    except Exception as e:
        logging.error(f"[MemoryModel] Error logging forgetting curve for '{concept}': {e}")
        return 0.0

# -----------------------------
# SELF-TEST / DEMO
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
