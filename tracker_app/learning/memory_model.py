"""Attention-Weighted Forgetting Curve (AWFC) retention model.

Standard Ebbinghaus: R(t) = exp(-Î» * t)
FKT AWFC:            R(t) = exp(-Î»_p * t), Î»_p = Î»_base * (1 - attention_norm * Î±)
A concept learned at 80% attention decays ~24% slower than one at 15% attention.
"""

import math
import logging
from datetime import datetime, timedelta
from typing import Optional

from tracker_app.utils import utcnow as _utcnow

from tracker_app.config import DEFAULT_LAMBDA, MEMORY_THRESHOLD


logger = logging.getLogger("MemoryModel")

AWFC_ALPHA       = 0.30    # dampening factor â€” max slowdown from attention
LAMBDA_FLOOR     = 0.01    # minimum decay rate (concept never fully immortal)
LAMBDA_CEIL      = 0.50    # maximum decay rate


# â”€â”€â”€ Datetime helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def safe_parse_datetime(dt_value, default=None) -> datetime:
    """Parse datetime from string, datetime, or None."""
    if default is None:
        default = _utcnow()
    if isinstance(dt_value, datetime):
        return dt_value
    if not isinstance(dt_value, str) or not dt_value.strip():
        return default
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            return datetime.strptime(dt_value, fmt)
        except ValueError:
            continue
    return default


# â”€â”€â”€ AWFC core â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def compute_awfc_lambda(
    base_lambda: float,
    attention_at_encoding: float,
    alpha: float = AWFC_ALPHA,
) -> float:
    """
    Compute personalised decay constant Î»_p.

    Higher attention at time of learning â†’ slower forgetting (lower Î»_p).

    Args:
        base_lambda:           Default decay rate (from config, typically 0.1)
        attention_at_encoding: Attention score 0â€“100 when concept was first captured
        alpha:                 Dampening factor â€” 0.3 means 80% attention â†’ 24% slower decay

    Returns:
        Personalised lambda in [LAMBDA_FLOOR, LAMBDA_CEIL]
    """
    att_norm = max(0.0, min(attention_at_encoding / 100.0, 1.0))
    lambda_p  = base_lambda * (1.0 - att_norm * alpha)
    return max(LAMBDA_FLOOR, min(lambda_p, LAMBDA_CEIL))


def compute_memory_score_awfc(
    last_review: datetime,
    base_lambda: float = DEFAULT_LAMBDA,
    attention_at_encoding: float = 50.0,
    modality_boost: float = 1.0,
) -> float:
    """
    Compute retention probability using AWFC.

    R(t) = exp(-Î»_p * t) * modality_boost
    Clamped to [0.05, 1.0] â€” never reports 0% (uncertainty floor).

    Args:
        last_review:            When the concept was last seen or reviewed
        base_lambda:            Base decay constant
        attention_at_encoding:  Attention at time of learning (0â€“100)
        modality_boost:         Extra retention from multi-modal engagement

    Returns:
        Float in [0.05, 1.0]
    """
    lambda_p = compute_awfc_lambda(base_lambda, attention_at_encoding)
    t_hours  = max(0.0, (_utcnow() - last_review).total_seconds() / 3600.0)
    R        = math.exp(-lambda_p * t_hours) * modality_boost
    return max(0.05, min(1.0, R))


# â”€â”€â”€ Review scheduling â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def schedule_next_review(
    last_review_time,
    memory_score: float,
    lambda_val: float,
    attention_at_encoding: float = 50.0,
    hours_min: float = 1.0,
) -> datetime:
    """
    Compute optimal next review time based on AWFC memory score.

    Weak memory â†’ review soon.
    Strong memory â†’ longer interval, scaled by personalised Î».
    """
    last_review = safe_parse_datetime(last_review_time)
    lambda_p    = compute_awfc_lambda(lambda_val, attention_at_encoding)

    if memory_score < MEMORY_THRESHOLD:
        interval_hours = hours_min
    else:
        base_interval  = 1.0 / max(0.01, lambda_p)
        strength_factor = memory_score ** 2
        interval_hours  = max(hours_min, base_interval * strength_factor)
        interval_hours  = min(interval_hours, 24 * 30)  # cap at 30 days

    return _utcnow() + timedelta(hours=interval_hours)


# â”€â”€â”€ Personalise Î» from review history â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def recalibrate_lambda(
    concept: str,
    current_lambda: float,
    actual_success_rate: float,
    n_reviews: int,
    last_seen: Optional[datetime] = None,
) -> float:
    """
    Adjust personalised Î» based on actual vs. predicted recall.

    Only fires after 5+ reviews to avoid noise.
    If user recalls better than predicted â†’ reduce Î» (slower decay).
    If user recalls worse â†’ increase Î» (faster decay, more reviews).

    Returns updated lambda value.
    """
    if n_reviews < 5:
        return current_lambda

    if last_seen is None:
        last_seen = _utcnow() - timedelta(days=7)

    # Decay window = time since the LAST review/encounter (last_seen), not
    # the concept's total age. first_seen makes predicted retention ~0 for
    # any long-lived concept (exp(-0.1 * 2000) ~= 0), so the adjustment
    # stops responding to actual recall and drives lambda to a bound (H-3).
    t_hours = (_utcnow() - last_seen).total_seconds() / 3600.0
    predicted_rate = math.exp(-current_lambda * t_hours) if t_hours > 0 else 1.0

    # Nudge Î» toward the right decay rate
    adjustment  = 0.05 * (predicted_rate - actual_success_rate)
    new_lambda  = current_lambda + adjustment
    return max(LAMBDA_FLOOR, min(new_lambda, LAMBDA_CEIL))


if __name__ == "__main__":
    # Quick smoke test
    from datetime import timedelta
    learned_5h_ago = _utcnow() - timedelta(hours=5)

    for att in [20, 50, 80]:
        score = compute_memory_score_awfc(learned_5h_ago,
                                          base_lambda=0.1,
                                          attention_at_encoding=att)
        lp    = compute_awfc_lambda(0.1, att)
        print(f"Attention={att:>3}  Î»_p={lp:.4f}  retention={score:.4f}")

    next_rev = schedule_next_review(learned_5h_ago, memory_score=0.55,
                                    lambda_val=0.1, attention_at_encoding=75)
    print(f"\nNext review at: {next_rev.strftime('%Y-%m-%d %H:%M')} UTC")

