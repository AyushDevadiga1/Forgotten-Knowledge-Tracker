# ==========================================================
# core/ocr_module.py | IEEE Upgrade Layer (v2 + logging + type hints + lazy load + safe-fallbacks)
# ==========================================================

import cv2
import numpy as np
import re
from mss import mss
from functools import lru_cache
import logging
from typing import TYPE_CHECKING, List, Dict, Any, Optional

from core.knowledge_graph import get_graph
from config import TESSERACT_PATH

# -----------------------------
# Setup logging (don't reconfigure globally in library code)
# -----------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# -----------------------------
# Only set Tesseract if exists
# -----------------------------
try:
    import pytesseract  # keep import lazy-safe
    if TESSERACT_PATH and isinstance(TESSERACT_PATH, str) and TESSERACT_PATH.strip():
        try:
            if pytesseract and TESSERACT_PATH and __import__("os").path.isfile(TESSERACT_PATH):
                pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
            else:
                logger.warning(f"Tesseract not found at configured path: {TESSERACT_PATH}. OCR will fallback to empty output.")
        except Exception as e:
            logger.warning(f"Unable to set pytesseract cmd: {e}")
    else:
        logger.warning("TESSERACT_PATH empty; OCR will fallback to empty output.")
except Exception as e:
    # pytesseract import failed — mark as unavailable
    pytesseract = None
    logger.warning(f"pytesseract unavailable: {e}")

# -----------------------------
# Lazy-load models (safe)
# -----------------------------
if TYPE_CHECKING:
    from keybert import KeyBERT  # type: ignore
    from sentence_transformers import SentenceTransformer  # type: ignore

_kw_model: Optional["KeyBERT"] = None
_embedding_model: Optional["SentenceTransformer"] = None
_nlp = None

def get_kw_model():
    global _kw_model
    if _kw_model is not None:
        return _kw_model
    try:
        logger.info("Loading KeyBERT model...")
        from keybert import KeyBERT  # type: ignore
        _kw_model = KeyBERT()
        return _kw_model
    except Exception as e:
        logger.warning(f"Failed to load KeyBERT: {e}")
        _kw_model = None
        return None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    try:
        logger.info("Loading SentenceTransformer model...")
        from sentence_transformers import SentenceTransformer  # type: ignore
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        return _embedding_model
    except Exception as e:
        logger.warning(f"Failed to load SentenceTransformer: {e}")
        _embedding_model = None
        return None

def get_nlp_model():
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        logger.info("Loading spaCy model...")
        import spacy  # type: ignore
        _nlp = spacy.load("en_core_web_sm")
        return _nlp
    except Exception as e:
        logger.warning(f"Failed to load spaCy model: {e}")
        _nlp = None
        return None

# -----------------------------
# Constants / defaults
# -----------------------------
# NOTE: keep embedding dim aligned with model; fallback uses 384 (all-MiniLM-L6-v2 -> 384)
FALLBACK_EMBEDDING_DIM = 384

# -----------------------------
# Screenshot capture (safe)
# -----------------------------
def capture_screenshot() -> Optional[np.ndarray]:
    """
    Returns BGR image array, or None if capture failed.
    """
    try:
        with mss() as sct:
            # defend against monitors index errors
            monitors = sct.monitors
            if not monitors or len(monitors) < 2:
                # no monitors available
                logger.warning("No monitor found for screenshot capture.")
                return None
            # default to primary monitor (index 1)
            screenshot = sct.grab(monitors[1])
            img = np.array(screenshot)
            # if alpha present convert to BGR, else ensure BGR
            if img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            elif img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            return img
    except Exception as e:
        logger.warning(f"Screenshot capture failed: {e}")
        return None

# -----------------------------
# Image preprocessing (safe)
# -----------------------------
def preprocess_image(img: Optional[np.ndarray]) -> Optional[np.ndarray]:
    """
    Converts to grayscale and enhances contrast. Returns None if input invalid.
    """
    if img is None:
        logger.debug("preprocess_image received None")
        return None
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        return gray
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}")
        return None

# -----------------------------
# OCR extraction (safe)
# -----------------------------
def extract_text(img: Optional[np.ndarray]) -> str:
    """
    Returns extracted text or empty string if OCR not available or failed.
    """
    if img is None:
        logger.debug("extract_text received None image -> returning empty string")
        return ""

    if pytesseract is None:
        logger.debug("pytesseract not available -> returning empty string")
        return ""

    custom_config = r'--oem 3 --psm 6'
    try:
        # pytesseract can accept numpy array directly
        text = pytesseract.image_to_string(img, config=custom_config)
        if not isinstance(text, str):
            return ""
        return text
    except Exception as e:
        logger.warning(f"OCR extraction failed: {e}")
        return ""

# -----------------------------
# Keyword extraction (old pipeline) - defensive
# -----------------------------
def extract_keywords(text: str, top_n: int = 15, boost_repeats: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Returns mapping keyword -> {"score": float} (keeps old shape but safer).
    If KeyBERT or spaCy unavailable, falls back to simple token heuristics.
    """
    if not text:
        return {}

    kw_dict: Dict[str, float] = {}

    # Try KeyBERT
    kw_model = get_kw_model()
    try:
        if kw_model is not None:
            kw_list = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2),
                                                stop_words='english', top_n=top_n*2)
            for k, score in kw_list:
                if isinstance(k, str):
                    kw_dict[k.lower()] = float(score)
    except Exception as e:
        logger.warning(f"KeyBERT extraction failed: {e}")

    # Try spaCy to augment keywords
    nlp = get_nlp_model()
    try:
        if nlp is not None:
            doc = nlp(text)
            nlp_keywords = [token.lemma_.lower() for token in doc
                            if token.is_alpha and not token.is_stop and token.pos_ in ("NOUN", "PROPN")]
            entities = [ent.text.lower() for ent in doc.ents]
            for kw in nlp_keywords + entities:
                if kw and kw not in kw_dict:
                    kw_dict[kw] = max(kw_dict.get(kw, 0.0), 0.3)
    except Exception as e:
        logger.warning(f"spaCy keyword augmentation failed: {e}")

    # fallback simple tokenization if we have nothing
    if not kw_dict:
        tokens = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", text)]
        freq: Dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        # pick most frequent tokens
        for k, v in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n]:
            kw_dict[k] = float(v) / max(1, len(tokens))

    # split camel/case and further normalize keys (keep your splitting behavior)
    split_keywords: Dict[str, float] = {}
    for kw, score in kw_dict.items():
        parts = re.split(r'[_\s]', kw)
        for part in parts:
            camel_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', part)
            for p in camel_parts:
                p = p.lower()
                if len(p) > 2:
                    split_keywords[p] = max(score, split_keywords.get(p, 0.0))
    kw_dict = split_keywords

    # boost repeats
    if boost_repeats:
        word_counts: Dict[str, int] = {}
        for word in text.lower().split():
            word_counts[word] = word_counts.get(word, 0) + 1
        for kw in list(kw_dict.keys()):
            if kw in word_counts and word_counts[kw] > 1:
                kw_dict[kw] = kw_dict.get(kw, 0.0) + 0.1 * (word_counts[kw] - 1)

    # boost if present in knowledge graph
    try:
        G = get_graph()
        for kw in list(kw_dict.keys()):
            if G is not None and hasattr(G, "nodes") and kw in G.nodes:
                kw_dict[kw] = kw_dict.get(kw, 0.0) + 0.2
    except Exception as e:
        logger.warning(f"Knowledge graph check failed: {e}")

    # produce sorted top_n and final shape
    sorted_keywords = dict(sorted(kw_dict.items(), key=lambda x: x[1], reverse=True))
    top_items = list(sorted_keywords.items())[:top_n]
    result: Dict[str, Dict[str, Any]] = {}
    for kw, score in top_items:
        result[kw] = {"score": float(score)}
    return result

# -----------------------------
# Sentence embeddings (safe)
# -----------------------------
def get_embeddings(text: str) -> np.ndarray:
    """
    Returns embedding vector as numpy array. On failure returns zero vector of fallback dimension.
    """
    if not text:
        return np.zeros(FALLBACK_EMBEDDING_DIM, dtype=float)

    emb_model = get_embedding_model()
    if emb_model is None:
        logger.debug("Embedding model unavailable; returning zero vector.")
        return np.zeros(FALLBACK_EMBEDDING_DIM, dtype=float)

    try:
        vec = emb_model.encode([text])
        if hasattr(vec, "__len__"):
            # vec may be shape (1, dim)
            vec0 = np.array(vec)[0]
            return np.asarray(vec0)
        else:
            return np.asarray(vec)
    except Exception as e:
        logger.warning(f"Embedding computation failed: {e}")
        return np.zeros(FALLBACK_EMBEDDING_DIM, dtype=float)

# ==========================================================
# IEEE-Ready Concept Extraction Layer (v2) - cached & safe
# ==========================================================
@lru_cache(maxsize=64)
def extract_concepts(text: str, top_n: int = 5) -> List[str]:
    if not text:
        return []
    kw_model = get_kw_model()
    try:
        if kw_model is None:
            # fallback: use regex tokens
            tokens = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", text)]
            unique = []
            for t in tokens:
                if t not in unique:
                    unique.append(t)
            return unique[:top_n]
        kw_list = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,3),
                                            stop_words='english', top_n=top_n*3)
        unique_concepts: List[str] = []
        for k, _ in kw_list:
            key = k.lower()
            if key not in unique_concepts:
                unique_concepts.append(key)
        return unique_concepts[:top_n]
    except Exception as e:
        logger.warning(f"extract_concepts_v2 fallback: {e}")
        return []

def get_text_embedding(text: str) -> np.ndarray:
    """
    Wrapper that returns a stable-length embedding (numpy array).
    """
    if not text:
        return np.zeros(FALLBACK_EMBEDDING_DIM, dtype=float)
    try:
        return get_embeddings(text)
    except Exception as e:
        logger.warning(f"get_text_embedding_v2 fallback: {e}")
        return np.zeros(FALLBACK_EMBEDDING_DIM, dtype=float)

# -----------------------------
# v2 OCR pipeline (safe end-to-end)
# -----------------------------
def ocr_pipeline() -> Dict[str, Any]:
    img = capture_screenshot()
    processed = preprocess_image(img)
    text = extract_text(processed)

    concepts = extract_concepts(text)
    emb = get_text_embedding(text)

    keywords_with_scores = extract_keywords(text, top_n=15)
    text_lower = text.lower() if text else ""
    keywords_with_counts: Dict[str, Dict[str, Any]] = {}
    for kw, meta in keywords_with_scores.items():
        try:
            score = float(meta.get("score", 0.0)) if isinstance(meta, dict) else float(meta)
        except Exception:
            score = 0.0
        count = text_lower.split().count(kw.lower()) if kw else 0
        keywords_with_counts[str(kw)] = {"score": float(score), "count": int(count)}

    logger.info(f"OCR pipeline processed {len(keywords_with_counts)} keywords and {len(concepts)} concepts.")

    return {
        "raw_text": str(text),
        "keywords": keywords_with_counts,
        "concepts_v2": concepts,
        "embedding_v2": emb.tolist() if isinstance(emb, np.ndarray) else list(np.asarray(emb))
    }

# -----------------------------
# Test run
# -----------------------------
if __name__ == "__main__":
    res = ocr_pipeline()
    print("Concepts v2:", res.get('concepts_v2'))
    print("Keywords (old):", res['keywords'])
    print("Text snippet:", res['raw_text'][:300])
