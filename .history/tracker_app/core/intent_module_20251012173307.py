# core/intent_module.py
"""
Intent Module (IEEE-Ready v3, Temporal Smoothing + Lazy Load)
--------------------------------------------------------------
- Predicts user intent based on multi-modal signals (OCR, audio, attention, interaction)
- Uses trained classifier if available; otherwise applies fallback rules
- Normalizes features to 0-1 scale
- Maintains short-term history for temporal smoothing
- Logs predictions safely to multi_modal_logs table
"""
from typing import Union, List, Dict, Optional, Any

import numpy as np
import pickle
import os
import logging
from typing import Union, List, Dict, Optional
from collections import deque
from core.db_module import log_multi_modal_event
from core import memory_model, knowledge_graph
from datetime import datetime
# -----------------------------
# Logging setup
# -----------------------------
if not os.path.exists("logs"):
    os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("IntentModule")
if not logger.handlers:
    handler = logging.FileHandler("logs/intent_module.log")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# -----------------------------
# Paths
# -----------------------------
CLF_PATH = "core/intent_classifier.pkl"
MAP_PATH = "core/intent_label_map.pkl"

# -----------------------------
# Lazy-load classifier & label map
# -----------------------------
_intent_clf: Optional[any] = None
_intent_label_map: Optional[any] = None

def get_intent_clf():
    global _intent_clf
    if _intent_clf is not None:
        return _intent_clf
    try:
        if os.path.exists(CLF_PATH):
            with open(CLF_PATH, "rb") as f:
                _intent_clf = pickle.load(f)
            logger.info("Intent classifier loaded lazily.")
        else:
            logger.warning("Intent classifier not found; fallback rules only.")
    except Exception as e:
        logger.error(f"Failed to load classifier: {e}")
        _intent_clf = None
    return _intent_clf

def get_label_map():
    global _intent_label_map
    if _intent_label_map is not None:
        return _intent_label_map
    try:
        if os.path.exists(MAP_PATH):
            with open(MAP_PATH, "rb") as f:
                _intent_label_map = pickle.load(f)
            logger.info("Intent label map loaded lazily.")
        else:
            logger.warning("Intent label map not found; numeric predictions will be stringified.")
    except Exception as e:
        logger.error(f"Failed to load label map: {e}")
        _intent_label_map = None
    return _intent_label_map

# -----------------------------
# Temporal smoothing
# -----------------------------
HISTORY_LENGTH = 5
_intent_history: deque = deque(maxlen=HISTORY_LENGTH)

def smooth_intent(pred_label: str, confidence: float) -> Dict[str, Union[str, float]]:
    _intent_history.append({"label": pred_label, "confidence": confidence})
    labels = [x["label"] for x in _intent_history]
    confs = [x["confidence"] for x in _intent_history]

    # Majority vote for label
    label_counts = {lbl: labels.count(lbl) for lbl in set(labels)}
    majority_label = max(label_counts, key=label_counts.get)
    avg_conf = float(np.mean(confs))

    return {"intent_label": majority_label, "confidence": avg_conf}

def extract_features(
    ocr_keywords: Union[List[str], Dict[str, Any]],  # include memory_score
    audio_label: str,
    attention_score: float,
    interaction_rate: float,
    use_webcam: bool = False
) -> np.ndarray:
    """
    Extract normalized features for intent prediction.
    Memory scores of OCR keywords are integrated as weighted OCR input.
    """
    try:
        # OCR value: weighted by memory score
        ocr_val = 0.0
        if isinstance(ocr_keywords, dict):
            for kw, meta in ocr_keywords.items():
                score = meta.get("score", 0.0)
                mem = meta.get("memory_score", 1.0)  # default 1.0
                ocr_val += score * (1.0 - mem)  # weight higher for low memory
        elif isinstance(ocr_keywords, list):
            ocr_val = len(ocr_keywords)

        audio_map = {"speech": 2, "music": 1, "silence": 0}
        audio_val = audio_map.get(str(audio_label).lower(), 0)

        att_val = float(attention_score) / 100.0 if isinstance(attention_score, (int, float)) else 0.5
        interaction_val = float(interaction_rate) / 20.0 if isinstance(interaction_rate, (int, float)) else 0.0

        # Normalize OCR count assuming top ~20 weighted keywords
        ocr_norm = min(ocr_val / 20.0, 1.0)

        features = np.array([ocr_norm, audio_val/2.0, att_val, interaction_val]).reshape(1, -1)
        return features
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        return np.array([[0.0, 0.0, 0.5, 0.0]])

# -----------------------------
# Updated Predict Intent
# -----------------------------
def predict_intent(
    ocr_keywords: Union[List[str], Dict[str, Any]],
    audio_label: str,
    attention_score: float,
    interaction_rate: float,
    use_webcam: bool = False
) -> Dict[str, Union[str, float]]:
    """
    Predict user intent using memory-weighted OCR features.
    """
    try:
        # Extract features with memory-weighted OCR
        features = extract_features(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam)
        clf = get_intent_clf()
        label_map = get_label_map()

        if clf:
            pred = clf.predict(features)[0]
            if label_map and hasattr(label_map, "inverse_transform"):
                label = label_map.inverse_transform([pred])[0]
            else:
                label = str(pred)
            confidence = float(max(clf.predict_proba(features)[0]))
        else:
            # Fallback rules
            audio_label_safe = str(audio_label).lower()
            if audio_label_safe == "speech" and interaction_rate > 5:
                label, confidence = ("studying", 0.8) if (use_webcam and attention_score > 50) else ("passive", 0.6)
            elif interaction_rate < 2:
                label, confidence = "idle", 0.7
            else:
                label, confidence = "passive", 0.6

        confidence = max(0.0, min(confidence, 1.0))
        smoothed = smooth_intent(label, confidence)

        # Centralized logging with memory scores
        try:
            mem_score_avg = None
            if isinstance(ocr_keywords, dict) and ocr_keywords:
                mem_vals = [meta.get("memory_score", 1.0) for meta in ocr_keywords.values()]
                mem_score_avg = float(np.mean(mem_vals))

            log_multi_modal_event(
                window_title=f"Intent Prediction: {smoothed['intent_label']}",
                ocr_keywords=str(list(ocr_keywords.keys()) if isinstance(ocr_keywords, dict) else ocr_keywords),
                audio_label=audio_label,
                attention_score=attention_score,
                interaction_rate=interaction_rate,
                intent_label=smoothed["intent_label"],
                intent_confidence=smoothed["confidence"],
                memory_score=mem_score_avg,
                source_module="IntentModule"
            )
        except Exception as log_e:
            logger.error(f"Logging failed: {log_e}")

        return smoothed
    except Exception as e:
        logger.error(f"Intent prediction failed: {e}")
        return {"intent_label": "unknown", "confidence": 0.0}

