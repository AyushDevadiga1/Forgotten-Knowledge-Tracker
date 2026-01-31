# ==========================================================
# core/intent_module.py | FKT v4 Async
# ==========================================================
"""
Intent Module v4 (IEEE-ready Async)
----------------------------------
- Predicts user intent from multi-modal inputs
- Async-friendly, fault-tolerant
- Integrates OCR keywords, Audio labels, Attention scores
- Returns structured dict for FusionPipeline v4
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
from core.memory_model import compute_memory_score

# ----------------------------- Logger Setup -----------------------------
logger = logging.getLogger("IntentModule")
if not logger.handlers:
    handler = logging.FileHandler("logs/intent_module_v4.log")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ----------------------------- Dummy / Fallback Model -----------------------------
INTENT_MAP = {
    "clear_speech": "Speaking",
    "speaking": "Speaking",
    "silence": "Silent",
    "reading": "Reading",
    "typing": "Typing",
    "observing": "Observing",
}

async def predict_intent(
    ocr_keywords: List[str],
    audio_label: str,
    attention_score: float,
    interaction_rate: float = 0.0,
    use_webcam: bool = True
) -> Dict[str, Any]:
    """
    Async intent prediction from multi-modal inputs
    """
    result: Dict[str, Any] = {
        "intent_label": "unknown",
        "confidence": 0.0,
        "timestamp": datetime.now().isoformat(),
        "reason": "",
        "memory_score": 0.0
    }

    try:
        # Simple heuristic for demonstration
        if audio_label.lower() in INTENT_MAP:
            label = INTENT_MAP[audio_label.lower()]
        elif "read" in " ".join(ocr_keywords).lower():
            label = "Reading"
        else:
            label = "Observing"

        # Compute confidence heuristically
        conf = min(max(attention_score / 100.0, 0.1), 0.99)

        # Optional: integrate memory score
        memory_score = compute_memory_score(datetime.now(), lambda_val=0.1, intent_conf=conf)

        # Update result
        result.update({
            "intent_label": label,
            "confidence": conf,
            "reason": f"Derived from audio={audio_label}, OCR={ocr_keywords[:3]}",
            "memory_score": memory_score
        })

    except Exception as e:
        logger.exception(f"Intent prediction failed: {e}")
        result.update({
            "intent_label": "unknown",
            "confidence": 0.0,
            "reason": f"Error: {e}",
            "memory_score": 0.0
        })

    return result
