"""Intent classification â€” trained RandomForest with rule-based fallback.

Feature vector: [ocr_keyword_count, audio_val, attention_score,
                 interaction_rate, keyword_avg_score, audio_confidence]
"""

import pickle
import logging
import numpy as np
import re
from pathlib import Path
from typing import Union, List, Dict

logger = logging.getLogger("IntentModule")

# â”€â”€ Model path â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MODEL_PATH = Path(__file__).parent.parent / "models" / "intent_classifier.pkl"

# â”€â”€ Lazy-loaded model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_model_data = None
_model_loaded = False


def _load_model():
    """Load trained classifier from disk (once). Returns model or None."""
    global _model_data, _model_loaded
    if _model_loaded:
        return _model_data
    _model_loaded = True
    if MODEL_PATH.exists():
        try:
            with open(MODEL_PATH, "rb") as f:
                _model_data = pickle.load(f)
            acc = _model_data.get("test_accuracy", 0)
            logger.info(f"Intent classifier loaded. Test accuracy: {acc:.2%}")
        except Exception as e:
            logger.warning(f"Failed to load intent model: {e}. Using rule fallback.")
            _model_data = None
    else:
        logger.warning(
            f"Intent model not found at {MODEL_PATH}. "
            "Run tracker_app/scripts/train_models_from_logs.py to train. "
            "Using rule-based fallback."
        )
    return _model_data


# â”€â”€ Feature engineering â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _safe_float(v, default=0.0):
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def extract_features(
    ocr_keywords: Union[List, Dict],
    audio_label: str,
    attention_score: float,
    interaction_rate: float,
    audio_confidence: float = 0.7,
) -> np.ndarray:
    """
    Build the 6-feature vector consumed by the classifier.

    Features:
      0  ocr_keyword_count   â€” number of unique keywords on screen
      1  audio_val           â€” 0=silence, 1=music, 2=speech
      2  attention_score     â€” 0â€“100 (CLE or webcam blend)
      3  interaction_rate    â€” input events / second in this cycle
      4  keyword_avg_score   â€” mean relevance of OCR keywords (0â€“1)
      5  audio_confidence    â€” audio classifier confidence (0â€“1)
    """
    # Feature 0: keyword count
    if isinstance(ocr_keywords, dict):
        kw_count = len(ocr_keywords)
        # keyword_avg_score: mean of score values (dict values are score or nested dicts)
        scores = []
        for v in ocr_keywords.values():
            if isinstance(v, dict):
                scores.append(_safe_float(v.get("score", 0.5)))
            else:
                scores.append(_safe_float(v, 0.5))
        kw_avg_score = float(np.mean(scores)) if scores else 0.0
    elif isinstance(ocr_keywords, (list, tuple)):
        kw_count = len(ocr_keywords)
        kw_avg_score = 0.5  # no scores available
    else:
        kw_count = 0
        kw_avg_score = 0.0

    # Feature 1: audio numeric
    audio_map = {"speech": 2, "music": 1, "silence": 0, "unknown": 0}
    audio_val = audio_map.get(str(audio_label).lower(), 0)

    # Feature 2: attention score clamped
    att = max(0.0, min(100.0, _safe_float(attention_score, 50.0)))

    # Feature 3: interaction rate clamped
    inter = max(0.0, min(100.0, _safe_float(interaction_rate, 0.0)))

    # Feature 5: audio confidence clamped
    aconf = max(0.0, min(1.0, _safe_float(audio_confidence, 0.7)))

    return np.array([[kw_count, audio_val, att, inter, kw_avg_score, aconf]], dtype=np.float32)

# ---- Content-awareness (rule-level, no feature-vector change) ----
RELEVANCE_HIGH = 0.30      # screen matches study topics strongly enough to promote
RELEVANCE_LOW = 0.05       # screen matches almost nothing -> demote studying
MIN_CONTENT_KEYWORDS = 3   # need enough on-screen keywords before relevance matters

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _keyword_score(value) -> float:
    """Score from extract_keywords' value, either a float or a dict holding 'score'."""
    if isinstance(value, dict):
        return _safe_float(value.get("score", 0.5))
    return _safe_float(value, 0.5)


def _tokenize(phrase: str) -> set:
    """Lowercase alphanumeric tokens (len >= 3) from a phrase or concept."""
    return {t for t in _TOKEN_RE.findall(str(phrase).lower()) if len(t) >= 3}


def compute_content_relevance(ocr_keywords: Union[List, Dict], known_concepts: List[str]) -> float:
    """Weighted fraction of on-screen keywords that share a token with a known study concept.

    Deterministic lexical overlap (no embedding model): a keyword matches when any of its
    len>=3 tokens appears in any concept's token set. Weights are the keyword scores, so
    real, higher-scored content keywords drive relevance more than chrome noise.

    Returns 0.0 when there is nothing to compare.
    """
    kw = ocr_keywords if isinstance(ocr_keywords, dict) else {}
    if not kw or not known_concepts:
        return 0.0

    concept_tokens = set()
    for c in known_concepts:
        concept_tokens |= _tokenize(c)

    total_score = 0.0
    matched_score = 0.0
    for phrase, value in kw.items():
        score = _keyword_score(value)
        total_score += score
        if _tokenize(phrase) & concept_tokens:
            matched_score += score
    if total_score <= 0:
        return 0.0
    return min(1.0, matched_score / total_score)


def _load_known_concepts() -> List[str]:
    """Lazy-load the user's study concepts from the knowledge graph; [] on failure."""
    try:
        from tracker_app.tracking.knowledge_graph import get_graph

        g = get_graph()
        return [n for n in g.nodes() if isinstance(n, str) and len(n) > 2]
    except Exception as e:
        logger.debug("knowledge-graph load failed for content relevance: %s", e)
        return []


# â”€â”€ Rule-based fallback (v1 logic, kept as safety net) â”€â”€â”€
_RULE_MAP = [
    # (condition_fn)  â†’  (label, confidence)
    (lambda kw, au, at, ir: au == "speech" and ir > 5 and at > 55, "studying", 0.72),
    (lambda kw, au, at, ir: len(kw) >= 6 and ir > 6 and at > 50, "studying", 0.68),
    (lambda kw, au, at, ir: ir < 2 and at < 35, "idle", 0.75),
    (lambda kw, au, at, ir: ir < 1, "idle", 0.70),
]


def _rule_predict(ocr_keywords, audio_label, attention_score, interaction_rate) -> Dict:
    kw = ocr_keywords if isinstance(ocr_keywords, (list, dict)) else []
    for cond, label, conf in _RULE_MAP:
        try:
            if cond(kw, audio_label, attention_score, interaction_rate):
                return {"intent_label": label, "confidence": conf, "source": "rules"}
        except Exception as exc:
            logger.debug("rule condition failed: %s", exc)
    return {"intent_label": "passive", "confidence": 0.58, "source": "rules"}


# â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def predict_intent(
    ocr_keywords: Union[List, Dict],
    audio_label: str = "silence",
    attention_score: float = 50.0,
    interaction_rate: float = 0.0,
    use_webcam: bool = False,
    audio_confidence: float = 0.7,
    known_concepts: Union[List[str], None] = None,
) -> Dict:
    """
    Predict user intent from multi-modal signals.

    known_concepts: optional study-history concepts to measure screen content
        against. When omitted, they are lazy-loaded from the knowledge graph,
        so callers (tracker loop, golden harness) can inject a deterministic set.

    Returns:
        {
            'intent_label': 'studying' | 'passive' | 'idle',
            'confidence':   float,
            'source':       'classifier' | 'rules' | 'rules+content',
            'features':     [f1, f2, f3, f4, f5, f6],  # exact vector fed to model
            'content_relevance': 0..1 # on-screen keyword overlap with study topics
        }
    """
    # Compute the feature vector once so the exact inputs used at prediction
    # time can be persisted for feedback-driven retraining (ADR-003).
    feats = extract_features(ocr_keywords, audio_label, attention_score, interaction_rate, audio_confidence)
    feature_list = [round(float(x), 4) for x in feats[0]]

    # Content awareness: compare on-screen keywords against the user's study
    # topics. Explicit concepts win over lazy knowledge-graph load (deterministic
    # in the golden harness; cheap in the loop).
    concepts = known_concepts if known_concepts is not None else _load_known_concepts()
    content_relevance = compute_content_relevance(ocr_keywords, concepts)

    model_data = _load_model()

    if model_data is not None:
        try:
            model = model_data["model"]
            label = model.predict(feats)[0]
            proba = model.predict_proba(feats)[0]
            confidence = float(np.max(proba))
            result = {
                "intent_label": str(label),
                "confidence": round(confidence, 4),
                "source": "classifier",
                "features": feature_list,
            }
        except Exception as e:
            logger.warning(f"Classifier prediction failed: {e}. Using rules.")
            result = _rule_predict(ocr_keywords, audio_label, attention_score, interaction_rate)
            result["features"] = feature_list
    else:
        # Fallback to rule-based
        result = _rule_predict(ocr_keywords, audio_label, attention_score, interaction_rate)
        result["features"] = feature_list

    # Rule-level content bias (applied AFTER the classifier; never touches the
    # persisted feature vector, so the feedback/training contract is unchanged).
    result["content_relevance"] = round(content_relevance, 4)
    kw_count = len(ocr_keywords) if isinstance(ocr_keywords, (list, dict)) else 0
    if kw_count >= MIN_CONTENT_KEYWORDS:
        if content_relevance >= RELEVANCE_HIGH and result["intent_label"] in ("passive", "idle"):
            result["intent_label"] = "studying"
            result["source"] = "rules+content"
        elif content_relevance <= RELEVANCE_LOW and result["intent_label"] == "studying":
            result["intent_label"] = "passive"
            result["source"] = "rules+content"
    return result


if __name__ == "__main__":
    cases = [
        {
            "ocr": {
                "photosynthesis": {"score": 0.9},
                "chlorophyll": {"score": 0.8},
                "reaction": {"score": 0.7},
                "membrane": {"score": 0.6},
                "glucose": {"score": 0.75},
                "enzyme": {"score": 0.65},
            },
            "audio": "speech",
            "att": 82,
            "ir": 14,
            "aconf": 0.9,
        },
        {"ocr": {"youtube": {"score": 0.3}}, "audio": "music", "att": 45, "ir": 2, "aconf": 0.8},
        {"ocr": {}, "audio": "silence", "att": 18, "ir": 0.2, "aconf": 0.95},
    ]
    for i, c in enumerate(cases, 1):
        r = predict_intent(c["ocr"], c["audio"], c["att"], c["ir"], audio_confidence=c["aconf"])
        print(f"Case {i}: {r['intent_label']:<10} conf={r['confidence']:.3f}  src={r['source']}")
