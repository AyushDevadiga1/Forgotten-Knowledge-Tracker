# ==========================================================
# core/ocr_module.py
# ==========================================================

"""
OCR Module (IEEE-Ready Async v3)
--------------------------------
- Async screenshot capture with optional ROI
- Safe preprocessing & OCR extraction
- Keyword extraction + Ebbinghaus-aware scoring
- Knowledge graph integration
- Embedding extraction (KeyBERT + SentenceTransformer)
- Structured multi-modal output for tracker
- Fully async-ready using asyncio.to_thread
"""

import cv2
import numpy as np
import re
import asyncio
from mss import mss
from functools import lru_cache
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from core import memory_model, knowledge_graph
from core.knowledge_graph import get_graph
from config import TESSERACT_PATH

# ----------------------------- Logger Setup -----------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ----------------------------- Tesseract Setup -----------------------------
try:
    import pytesseract
    if TESSERACT_PATH:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
except Exception as e:
    pytesseract = None
    logger.warning(f"pytesseract not available: {e}")

# ----------------------------- Lazy-loaded NLP & Embedding -----------------------------
_kw_model: Optional[Any] = None
_embedding_model: Optional[Any] = None
_nlp: Optional[Any] = None
FALLBACK_EMBEDDING_DIM = 384

def get_kw_model():
    global _kw_model
    if _kw_model is not None:
        return _kw_model
    try:
        from keybert import KeyBERT
        _kw_model = KeyBERT()
    except Exception as e:
        logger.warning(f"KeyBERT load failed: {e}")
        _kw_model = None
    return _kw_model

def get_embedding_model():
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    except Exception as e:
        logger.warning(f"SentenceTransformer load failed: {e}")
        _embedding_model = None
    return _embedding_model

def get_nlp_model():
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    except Exception as e:
        logger.warning(f"spaCy load failed: {e}")
        _nlp = None
    return _nlp

# ----------------------------- Screenshot capture -----------------------------
async def capture_screenshot(roi: Optional[Tuple[int,int,int,int]] = None) -> Optional[np.ndarray]:
    try:
        with mss() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            if roi:
                x, y, w, h = roi
                monitor = {"top": y, "left": x, "width": w, "height": h}
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)
            if img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            elif img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            return img
    except Exception as e:
        logger.warning(f"Screenshot capture failed: {e}")
        return None

# ----------------------------- Preprocessing & OCR -----------------------------
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

def extract_text(img: Optional[np.ndarray]) -> str:
    if img is None or pytesseract is None:
        return ""
    try:
        return str(pytesseract.image_to_string(img, config=r'--oem 3 --psm 6'))
    except Exception as e:
        logger.warning(f"OCR extraction failed: {e}")
        return ""

# ----------------------------- Keyword extraction -----------------------------
def extract_keywords(text: str, top_n: int = 15) -> Dict[str, Dict[str, Any]]:
    if not text:
        return {}
    kw_dict: Dict[str, float] = {}
    kw_model = get_kw_model()
    if kw_model:
        try:
            kws = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2), stop_words='english', top_n=top_n*2)
            for k, score in kws:
                kw_dict[k.lower()] = float(score)
        except Exception as e:
            logger.warning(f"KeyBERT extraction failed: {e}")
    nlp = get_nlp_model()
    if nlp:
        try:
            doc = nlp(text)
            nlp_kws = [token.lemma_.lower() for token in doc if token.is_alpha and not token.is_stop and token.pos_ in ("NOUN","PROPN")]
            entities = [ent.text.lower() for ent in doc.ents]
            for kw in nlp_kws + entities:
                if kw and kw not in kw_dict:
                    kw_dict[kw] = max(kw_dict.get(kw,0.0),0.3)
        except Exception as e:
            logger.warning(f"spaCy keyword augmentation failed: {e}")
    if not kw_dict:
        tokens = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", text)]
        freq = {}
        for t in tokens:
            freq[t] = freq.get(t,0)+1
        for k,v in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n]:
            kw_dict[k] = float(v)/max(1,len(tokens))
    try:
        G = get_graph()
        for kw in list(kw_dict.keys()):
            if G is not None and hasattr(G,'nodes') and kw in G.nodes:
                kw_dict[kw] += 0.2
    except Exception as e:
        logger.warning(f"Knowledge graph boost failed: {e}")
    top_items = dict(sorted(kw_dict.items(), key=lambda x:x[1], reverse=True)[:top_n])
    return {k: {"score": float(v)} for k,v in top_items.items()}

# ----------------------------- Embeddings -----------------------------
def get_embeddings(text: str) -> np.ndarray:
    if not text:
        return np.zeros(FALLBACK_EMBEDDING_DIM)
    model = get_embedding_model()
    if not model:
        return np.zeros(FALLBACK_EMBEDDING_DIM)
    try:
        vec = model.encode([text])
        return np.array(vec[0]) if hasattr(vec,'__len__') else np.array(vec)
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return np.zeros(FALLBACK_EMBEDDING_DIM)

# ----------------------------- Concept Extraction -----------------------------
@lru_cache(maxsize=64)
def extract_concepts(text: str, top_n: int = 5) -> List[str]:
    if not text:
        return []
    kw_model = get_kw_model()
    try:
        if not kw_model:
            tokens = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", text)]
            return list(dict.fromkeys(tokens))[:top_n]
        kws = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,3), stop_words='english', top_n=top_n*3)
        unique = []
        for k,_ in kws:
            key = k.lower()
            if key not in unique:
                unique.append(key)
        return unique[:top_n]
    except Exception as e:
        logger.warning(f"Concept extraction fallback: {e}")
        return []

# ----------------------------- Important Keyword Filter -----------------------------
def filter_important_keywords(keywords: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    try:
        G = get_graph()
        if G is None or not hasattr(G, "nodes"):
            return keywords
        return {kw: meta for kw, meta in keywords.items() if kw in G.nodes}
    except Exception as e:
        logger.warning(f"Filtering important keywords failed: {e}")
        return keywords

# ----------------------------- Async OCR pipeline -----------------------------
async def ocr_pipeline(roi: Optional[Tuple[int,int,int,int]] = None) -> Dict[str, Any]:
    img = await capture_screenshot(roi)
    processed = await asyncio.to_thread(preprocess_image, img)
    text = await asyncio.to_thread(extract_text, processed)
    concepts = await asyncio.to_thread(extract_concepts, text)
    emb = await asyncio.to_thread(get_embeddings, text)
    keywords_raw = await asyncio.to_thread(extract_keywords, text)
    keywords_filtered = await asyncio.to_thread(filter_important_keywords, keywords_raw)

    text_lower = text.lower() if text else ""
    keywords_with_counts: Dict[str, Dict[str, Any]] = {}
    now = datetime.now()
    G = get_graph()

    for kw, meta in keywords_filtered.items():
        score = float(meta.get("score", 0.0))
        count = text_lower.split().count(kw.lower())
        memory_score = memory_model.compute_memory_score(
            last_review_time=now, lambda_val=0.1, intent_conf=1.0, attention_score=50, audio_conf=1.0
        )
        next_review_time = memory_model.schedule_next_review(
            last_review_time=now, memory_score=memory_score, lambda_val=0.1, hours_min=1.0
        )
        try:
            if kw not in G.nodes:
                G.add_node(
                    kw, embedding=np.zeros(FALLBACK_EMBEDDING_DIM), count=1,
                    memory_score=memory_score, next_review_time=next_review_time,
                    created_at=now.isoformat(), source="ocr_pipeline", last_seen_ts=now.isoformat()
                )
            else:
                node = G.nodes[kw]
                node['memory_score'] = memory_score
                node['next_review_time'] = next_review_time
                node['last_seen_ts'] = now.isoformat()
                node['count'] += 1
        except Exception as e:
            logger.warning(f"Knowledge graph update failed for '{kw}': {e}")
        keywords_with_counts[str(kw)] = {
            "score": score, "count": count,
            "memory_score": memory_score,
            "next_review_time": next_review_time.isoformat()
        }

    logger.info(f"OCR pipeline processed {len(keywords_with_counts)} keywords asynchronously.")
    return {
        "raw_text": str(text),
        "keywords": keywords_with_counts,
        "concepts_v2": concepts,
        "embedding_v2": emb.tolist() if isinstance(emb, np.ndarray) else list(np.asarray(emb))
    }

# ----------------------------- Self-Test -----------------------------
if __name__ == "__main__":
    import asyncio
    result = asyncio.run(ocr_pipeline())
    print("Filtered Concepts:", result.get("concepts_v2"))
    print("Filtered Keywords:", result["keywords"])
    print("Text snippet:", result["raw_text"][:300])
