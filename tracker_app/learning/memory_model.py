# learning/memory_model.py — FKT 2.0 Phase 4
# Attention-Weighted Forgetting Curve (AWFC) — novel contribution.
#
# Standard Ebbinghaus: R(t) = exp(-λ * t)
# FKT AWFC:            R(t) = exp(-λ_p * t)
#   where λ_p = λ_base * (1 - attention_norm * α)
#   attention_norm = attention_at_encoding / 100
#   α = 0.30  (high attention slows decay by up to 30%)
#
# This means a concept learned with 80% attention decays 24% slower
# than one absorbed while idle (15% attention).

import math
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional

from tracker_app.config import DB_PATH, DEFAULT_LAMBDA, MEMORY_THRESHOLD

logger = logging.getLogger("MemoryModel")

DATETIME_FORMAT  = "%Y-%m-%d %H:%M:%S"
AWFC_ALPHA       = 0.30    # dampening factor — max slowdown from attention
LAMBDA_FLOOR     = 0.01    # minimum decay rate (concept never fully immortal)
LAMBDA_CEIL      = 0.50    # maximum decay rate


# ─── Datetime helpers ─────────────────────────────────────────────────────────

def safe_parse_datetime(dt_value, default=None) -> datetime:
    """Parse datetime from string, datetime, or None."""
    if default is None:
        default = datetime.utcnow()
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


# ─── AWFC core ────────────────────────────────────────────────────────────────

def compute_awfc_lambda(
    base_lambda: float,
    attention_at_encoding: float,
    alpha: float = AWFC_ALPHA,
) -> float:
    """
    Compute personalised decay constant λ_p.

    Higher attention at time of learning → slower forgetting (lower λ_p).

    Args:
        base_lambda:           Default decay rate (from config, typically 0.1)
        attention_at_encoding: Attention score 0–100 when concept was first captured
        alpha:                 Dampening factor — 0.3 means 80% attention → 24% slower decay

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

    R(t) = exp(-λ_p * t) * modality_boost
    Clamped to [0.05, 1.0] — never reports 0% (uncertainty floor).

    Args:
        last_review:            When the concept was last seen or reviewed
        base_lambda:            Base decay constant
        attention_at_encoding:  Attention at time of learning (0–100)
        modality_boost:         Extra retention from multi-modal engagement

    Returns:
        Float in [0.05, 1.0]
    """
    lambda_p = compute_awfc_lambda(base_lambda, attention_at_encoding)
    t_hours  = max(0.0, (datetime.utcnow() - last_review).total_seconds() / 3600.0)
    R        = math.exp(-lambda_p * t_hours) * modality_boost
    return max(0.05, min(1.0, R))


# ─── Legacy compatibility: multi-modal weighted score ─────────────────────────

def compute_memory_score(
    last_review_time,
    lambda_val: float,
    intent_conf: float = 1.0,
    attention_score: float = 50.0,
    audio_conf: float = 1.0,
) -> float:
    """
    Legacy wrapper — now delegates to AWFC.
    kept so existing callers don't break.
    """
    last_review = safe_parse_datetime(last_review_time)

    att_factor    = max(0.1, min(attention_score / 100.0, 1.0))
    intent_factor = max(0.3, min(intent_conf,  1.0))
    audio_factor  = max(0.5, min(audio_conf,   1.0))
    modality_boost = (att_factor * intent_factor * audio_factor) ** (1 / 3)

    return compute_memory_score_awfc(
        last_review,
        base_lambda=lambda_val,
        attention_at_encoding=attention_score,
        modality_boost=modality_boost,
    )


# ─── Review scheduling ────────────────────────────────────────────────────────

def schedule_next_review(
    last_review_time,
    memory_score: float,
    lambda_val: float,
    attention_at_encoding: float = 50.0,
    hours_min: float = 1.0,
) -> datetime:
    """
    Compute optimal next review time based on AWFC memory score.

    Weak memory → review soon.
    Strong memory → longer interval, scaled by personalised λ.
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

    return datetime.utcnow() + timedelta(hours=interval_hours)


# ─── Personalise λ from review history ───────────────────────────────────────

def recalibrate_lambda(
    concept: str,
    current_lambda: float,
    actual_success_rate: float,
    n_reviews: int,
    first_seen: Optional[datetime] = None,
) -> float:
    """
    Adjust personalised λ based on actual vs. predicted recall.

    Only fires after 5+ reviews to avoid noise.
    If user recalls better than predicted → reduce λ (slower decay).
    If user recalls worse → increase λ (faster decay, more reviews).

    Returns updated lambda value.
    """
    if n_reviews < 5:
        return current_lambda

    if first_seen is None:
        first_seen = datetime.utcnow() - timedelta(days=7)

    t_hours = (datetime.utcnow() - first_seen).total_seconds() / 3600.0
    predicted_rate = math.exp(-current_lambda * t_hours) if t_hours > 0 else 1.0

    # Nudge λ toward the right decay rate
    adjustment  = 0.05 * (predicted_rate - actual_success_rate)
    new_lambda  = current_lambda + adjustment
    return max(LAMBDA_FLOOR, min(new_lambda, LAMBDA_CEIL))


# ─── Ebbinghaus retention probability ────────────────────────────────────────

def forgetting_curve(t_hours: float, stability: float = 1.25) -> float:
    """Standard Ebbinghaus. stability = memory strength parameter."""
    try:
        return math.exp(-t_hours / stability)
    except Exception:
        return 0.0


# ─── DB logging (legacy) ─────────────────────────────────────────────────────

def log_forgetting_curve(
    concept: str,
    last_seen_time,
    observed_usage: int = 1,
    memory_strength: float = 1.25,
) -> float:
    """Compute and persist predicted recall to memory_decay table."""
    last_seen = safe_parse_datetime(last_seen_time)
    t_hours   = max(0.0, (datetime.utcnow() - last_seen).total_seconds() / 3600.0)
    predicted = forgetting_curve(t_hours, memory_strength)

    try:
        conn = sqlite3.connect(DB_PATH)
        c    = conn.cursor()
        c.execute(
            """INSERT INTO memory_decay
               (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (str(concept),
             last_seen.strftime(DATETIME_FORMAT),
             float(predicted),
             int(observed_usage),
             datetime.utcnow().strftime(DATETIME_FORMAT))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"log_forgetting_curve failed: {e}")

    return predicted


if __name__ == "__main__":
    # Quick smoke test
    from datetime import timedelta
    learned_5h_ago = datetime.utcnow() - timedelta(hours=5)

    for att in [20, 50, 80]:
        score = compute_memory_score_awfc(learned_5h_ago,
                                          base_lambda=0.1,
                                          attention_at_encoding=att)
        lp    = compute_awfc_lambda(0.1, att)
        print(f"Attention={att:>3}  λ_p={lp:.4f}  retention={score:.4f}")

    next_rev = schedule_next_review(learned_5h_ago, memory_score=0.55,
                                    lambda_val=0.1, attention_at_encoding=75)
    print(f"\nNext review at: {next_rev.strftime('%Y-%m-%d %H:%M')} UTC")
