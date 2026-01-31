# ==========================================================
# core/ocr_module.py | IEEE Upgrade Layer (v2 + logging + type hints + lazy load)
# ==========================================================

import cv2
import numpy as np
import pytesseract
from mss import mss
from config import TESSERACT_PATH
import re
from functools import lru_cache
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keybert import KeyBERT
    from sentence_transformers import SentenceTransformer


from core.knowledge_graph import get_graph

# -----------------------------
# Setup logging
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# -----------------------------
# Set tesseract executable path
# -----------------------------
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# -----------------------------
# Lazy-load models
# -----------------------------
_kw_model: "KeyBERT" = None
_embedding_model: "SentenceTransformer" = None
_nlp = None

def get_kw_model():
    global _kw_model
    if _kw_model is None:
        logging.info("Loading KeyBERT model...")
        from keybert import KeyBERT
        _kw_model = KeyBERT()
    return _kw_model

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        logging.info("Loading SentenceTransformer model...")
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model

def get_nlp_model():
    global _nlp
    if _nlp is None:
        logging.info("Loading spaCy model...")
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

# -----------------------------
# Screenshot capture
# -----------------------------
def capture_screenshot() -> np.ndarray:
    with mss() as sct:
        screenshot = sct.grab(sct.monitors[1])
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

# -----------------------------
# Image preprocessing
# -----------------------------
def preprocess_image(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    return gray

# -----------------------------
# OCR extraction
# -----------------------------
def extract_text(img: np.ndarray) -> str:
    custom_config = r'--oem 3 --psm 6'
    try:
        text = pytesseract.image_to_string(img, config=custom_config)
        return text
    except Exception as e:
        logging.warning(f"OCR extraction failed: {e}")
        return ""

# -----------------------------
# Keyword extraction (old pipeline)
# -----------------------------
def extract_keywords(text: str, top_n: int = 15, boost_repeats: bool = True) -> Dict[str, Dict[str, Any]]:
    kw_model = get_kw_model()
    nlp = get_nlp_model()
    
    kw_list = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2),
                                        stop_words='english', top_n=top_n*2)
    kw_dict = {kw[0].lower(): kw[1] for kw in kw_list}

    doc = nlp(text)
    nlp_keywords = [token.lemma_.lower() for token in doc
                    if token.is_alpha and not token.is_stop and token.pos_ in ("NOUN","PROPN")]
    entities = [ent.text.lower() for ent in doc.ents]
    for kw in nlp_keywords + entities:
        if kw not in kw_dict:
            kw_dict[kw] = 0.3

    split_keywords = {}
    for kw, score in kw_dict.items():
        parts = re.split(r'[_\s]', kw)
        final_parts = []
        for part in parts:
            camel_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', part)
            final_parts.extend(camel_parts)
        for p in final_parts:
            p = p.lower()
            if len(p) > 2:
                split_keywords[p] = max(score, split_keywords.get(p, 0.0))
    kw_dict = split_keywords

    if boost_repeats:
        word_counts = {}
        for word in text.lower().split():
            word_counts[word] = word_counts.get(word, 0) + 1
        for kw in kw_dict:
            if kw in word_counts and word_counts[kw] > 1:
                kw_dict[kw] += 0.1 * (word_counts[kw]-1)

    G = get_graph()
    for kw in kw_dict:
        if kw in G.nodes:
            kw_dict[kw] += 0.2

    sorted_keywords = dict(sorted(kw_dict.items(), key=lambda x: x[1], reverse=True))
    return dict(list(sorted_keywords.items())[:top_n])

# -----------------------------
# Sentence embeddings
# -----------------------------
def get_embeddings(text: str) -> np.ndarray:
    embedding_model = get_embedding_model()
    return embedding_model.encode([text])[0]

# ==========================================================
# IEEE-Ready Concept Extraction Layer (v2)
# ==========================================================
@lru_cache(maxsize=64)
def extract_concepts(text: str, top_n: int = 5) -> List[str]:
    kw_model = get_kw_model()
    if not text:
        return []

    try:
        kw_list = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,3),
                                            stop_words='english', top_n=top_n*3)
        unique_concepts = []
        for k, _ in kw_list:
            key = k.lower()
            if key not in unique_concepts:
                unique_concepts.append(key)
        return unique_concepts[:top_n]
    except Exception as e:
        logging.warning(f"extract_concepts_v2 fallback: {e}")
        return []

def get_text_embedding(text: str) -> np.ndarray:
    embedding_model = get_embedding_model()
    if not text:
        return np.zeros(384)
    try:
        return embedding_model.encode([text])[0]
    except Exception as e:
        logging.warning(f"get_text_embedding_v2 fallback: {e}")
        return np.zeros(384)

# -----------------------------
# v2 OCR pipeline
# -----------------------------
def ocr_pipeline() -> Dict[str, Any]:
    img = capture_screenshot()
    processed = preprocess_image(img)
    text = extract_text(processed)

    concepts = extract_concepts(text)
    emb = get_text_embedding(text)

    keywords_with_scores = extract_keywords(text, top_n=15)
    text_lower = text.lower()
    keywords_with_counts = {}
    for kw, score in keywords_with_scores.items():
        count = text_lower.split().count(kw.lower())
        keywords_with_counts[str(kw)] = {"score": float(score), "count": int(count)}

    logging.info(f"OCR pipeline processed {len(keywords_with_counts)} keywords and {len(concepts)} concepts.")

    return {
        "raw_text": str(text),
        "keywords": keywords_with_counts,
        "concepts_v2": concepts,
        "embedding_v2": emb.tolist()
    }

# -----------------------------
# Test run
# -----------------------------
if __name__ == "__main__":
    result = ocr_pipeline()
    print("Concepts v2:", result.get('concepts_v2'))
    print("Keywords (old):", result['keywords'])
    print("Text snippet:", result['raw_text'][:300])
