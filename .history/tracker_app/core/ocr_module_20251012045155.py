# ==========================================================
# core/ocr_module.py | IEEE-Ready v3
# ==========================================================
"""
OCR / Screen Text Module
------------------------
- Safe screenshot capture (MSS)
- Robust preprocessing & OCR extraction
- Keyword & concept extraction (KeyBERT + spaCy + fallback)
- Sentence embeddings (SentenceTransformer)
- Attentiveness reasoning based on OCR scenarios
- Structured, IEEE-ready return type
"""

import cv2
import numpy as np
import re
from mss import mss
from functools import lru_cache
import logging
from typing import Dict, Any, Optional, List

from core.knowledge_graph import get_graph
from config import TESSERACT_PATH
from core.db_module import log_multi_modal_event

# -----------------------------
# Logger setup
# -----------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# -----------------------------
# Tesseract setup
# -----------------------------
try:
    import pytesseract
    if TESSERACT_PATH:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
except Exception as e:
    pytesseract = None
    logger.warning(f"pytesseract unavailable: {e}")

# -----------------------------
# Lazy-loaded models
# -----------------------------
_kw_model: Optional["KeyBERT"] = None
_embedding_model: Optional["SentenceTransformer"] = None
_nlp = None
FALLBACK_EMBEDDING_DIM = 384

def get_kw_model():
    global _kw_model
    if _kw_model is None:
        try:
            from keybert import KeyBERT
            _kw_model = KeyBERT()
        except Exception as e:
            logger.warning(f"KeyBERT load failed: {e}")
    return _kw_model

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"SentenceTransformer load failed: {e}")
    return _embedding_model

def get_nlp_model():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.warning(f"spaCy load failed: {e}")
    return _nlp

# -----------------------------
# Screenshot capture
# -----------------------------
def capture_screenshot() -> Optional[np.ndarray]:
    try:
        with mss() as sct:
            monitors = sct.monitors
            if len(monitors) < 2:
                logger.warning("No monitor found for screenshot.")
                return None
            img = np.array(sct.grab(monitors[1]))
            if img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            elif img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            return img
    except Exception as e:
        logger.warning(f"Screenshot capture failed: {e}")
        return None

# -----------------------------
# Preprocessing
# -----------------------------
def preprocess_image(img: Optional[np.ndarray]) -> Optional[np.ndarray]:
    if img is None:
        return None
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        return gray
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}")
        return None

# -----------------------------
# OCR Extraction
# -----------------------------
def extract_text(img: Optional[np.ndarray]) -> str:
    if img is None or pytesseract is None:
        return ""
    try:
        text = pytesseract.image_to_string(img, config=r'--oem 3 --psm 6')
        return text if isinstance(text, str) else ""
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return ""

# -----------------------------
# Keyword extraction
# -----------------------------
def extract_keywords(text: str, top_n: int = 15) -> Dict[str, Dict[str, Any]]:
    if not text:
        return {}
    kw_dict: Dict[str, float] = {}
    try:
        kw_model = get_kw_model()
        if kw_model:
            for k, score in kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2),
                                                      stop_words='english', top_n=top_n*2):
                if isinstance(k, str):
                    kw_dict[k.lower()] = float(score)
    except Exception as e:
        logger.warning(f"KeyBERT extraction failed: {e}")

    # spaCy augmentation
    nlp = get_nlp_model()
    try:
        if nlp:
            doc = nlp(text)
            for token in doc:
                if token.is_alpha and not token.is_stop:
                    kw_dict[token.lemma_.lower()] = max(kw_dict.get(token.lemma_.lower(),0.0),0.3)
            for ent in doc.ents:
                kw_dict[ent.text.lower()] = max(kw_dict.get(ent.text.lower(),0.0),0.3)
    except Exception as e:
        logger.warning(f"spaCy keyword augmentation failed: {e}")

    # fallback
    if not kw_dict:
        tokens = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", text)]
        freq = {}
        for t in tokens: freq[t] = freq.get(t,0)+1
        for k, v in sorted(freq.items(), key=lambda x:x[1], reverse=True)[:top_n]:
            kw_dict[k] = float(v)/max(1,len(tokens))

    return {k: {"score": float(v)} for k, v in sorted(kw_dict.items(), key=lambda x:x[1], reverse=True)[:top_n]}

# -----------------------------
# Embedding extraction
# -----------------------------
def get_embeddings(text: str) -> np.ndarray:
    if not text:
        return np.zeros(FALLBACK_EMBEDDING_DIM, dtype=float)
    model = get_embedding_model()
    if model is None:
        return np.zeros(FALLBACK_EMBEDDING_DIM, dtype=float)
    try:
        vec = model.encode([text])[0]
        return np.asarray(vec)
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return np.zeros(FALLBACK_EMBEDDING_DIM, dtype=float)

# -----------------------------
# Concept extraction
# -----------------------------
@lru_cache(maxsize=64)
def extract_concepts(text: str, top_n: int = 5) -> List[str]:
    if not text:
        return []
    try:
        kw_model = get_kw_model()
        if kw_model:
            kws = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,3),
                                            stop_words='english', top_n=top_n*3)
            unique: List[str] = []
            for k,_ in kws:
                key = k.lower()
                if key not in unique: unique.append(key)
            return unique[:top_n]
    except Exception as e:
        logger.warning(f"Concept extraction failed: {e}")
    # fallback regex
    tokens = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", text)]
    unique = []
    for t in tokens:
        if t not in unique: unique.append(t)
    return unique[:top_n]

# -----------------------------
# OCR Pipeline + Scenario Mapping
# -----------------------------
def ocr_pipeline_v3() -> Dict[str, Any]:
    img = capture_screenshot()
    processed = preprocess_image(img)
    text = extract_text(processed)
    keywords = extract_keywords(text)
    concepts = extract_concepts(text)
    embedding = get_embeddings(text)

    # -----------------------------
    # Scenario mapping for attentiveness
    # -----------------------------
    attentive: Optional[bool] = None
    confidence: float = 0.5
    reason: str = "Ambiguous attention"

    if not text.strip():
        attentive = False
        confidence = 0.0
        reason = "No text detected on screen"
    elif len(keywords) >= 5:
        attentive = True
        confidence = min(1.0, 0.5 + 0.1*len(keywords))
        reason = "Multiple keywords detected; user likely following task"
    else:
        attentive = None
        confidence = 0.5
        reason = "Partial keywords detected; ambiguous attention"

    # -----------------------------
    # Log multi-modal event (optional)
    # -----------------------------
    try:
        log_multi_modal_event(
            window_title="OCR Module",
            ocr_keywords=list(keywords.keys()),
            audio_label=None,
            attention_score=confidence,
            interaction_rate=None,
            intent_label=None,
            intent_confidence=confidence,
            memory_score=None,
            source_module="OCRModule"
        )
    except Exception:
        logger.exception("Failed to log OCR event.")

    return {
        "raw_text": text,
        "keywords": keywords,
        "concepts_v2": concepts,
        "embedding_v2": embedding.tolist() if isinstance(embedding, np.ndarray) else list(embedding),
        "attentive": attentive,
        "confidence": confidence,
        "reason": reason,
        "intention": "Reading or following screen content"
    }

# -----------------------------
# SELF-TEST
# -----------------------------
if __name__ == "__main__":
    result = ocr_pipeline_v3()
    print("Attentive:", result["attentive"])
    print("Confidence:", result["confidence"])
    print("Reason:", result["reason"])
    print("Concepts v2:", result.get("concepts_v2"))
    print("Keywords:", list(result["keywords"].keys()))
    print("Text snippet:", result["raw_text"][:300])
