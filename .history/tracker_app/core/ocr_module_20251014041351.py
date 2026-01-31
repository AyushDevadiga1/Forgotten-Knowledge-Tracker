# core/ocr_module.py
import cv2
import numpy as np
import pytesseract
from mss import mss
from config import TESSERACT_PATH
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
import spacy
from core.knowledge_graph import get_graph
import re
from functools import lru_cache
from typing import Dict, Tuple

# Optional fallback OCR
_try_easyocr = False
try:
    import easyocr
    _try_easyocr = True
    # we'll initialize Reader lazily to avoid overhead at import
except Exception:
    _try_easyocr = False

# Local fallback utilities
try:
    from core.fallback_manager import redact_sensitive, get_fallback_strategy
except Exception:
    # minimal redact if fallback_manager not available
    def redact_sensitive(text: str) -> str:
        if not text:
            return text
        patterns = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}",
            "password": r"(?i)(password|pass|pwd)\s*[:=]\s*\S+",
            "name": r"(?i)(name|username|user)\s*[:=]\s*\S+",
        }
        for label, pattern in patterns.items():
            text = re.sub(pattern, f"[REDACTED_{label.upper()}]", text)
        return text

    def get_fallback_strategy(modality: str) -> str:
        return f"Fallback strategy for {modality} not configured"

# Set tesseract path
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Initialize models with error handling
kw_model = None
embedding_model = None
nlp = None
easyocr_reader = None

try:
    kw_model = KeyBERT()
    print("KeyBERT loaded successfully.")
except Exception as e:
    print(f"Error loading KeyBERT: {e}")

try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("SentenceTransformer loaded successfully.")
except Exception as e:
    print(f"Error loading SentenceTransformer: {e}")

try:
    nlp = spacy.load("en_core_web_sm")
    print("spaCy model loaded successfully.")
except Exception as e:
    print(f"Error loading spaCy model: {e}")

if _try_easyocr:
    try:
        # init lazily to avoid long import at startup; create reader now
        easyocr_reader = easyocr.Reader(['en'], gpu=False)
        print("EasyOCR reader initialized.")
    except Exception as e:
        easyocr_reader = None
        print(f"EasyOCR initialization failed: {e}")

# Simple module-level cache for last valid text
_last_valid_text = ""
_last_valid_confidence = 0.0

# -------------------------
# Capture / Preprocess
# -------------------------
def capture_screenshot() -> np.ndarray:
    """Capture screenshot safely (returns BGR image)"""
    try:
        with mss() as sct:
            monitor = sct.monitors[1]  # primary monitor
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)
            # mss returns BGRA on some platforms
            if img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
        return None

def preprocess_image(img: np.ndarray) -> np.ndarray:
    """Preprocess image for better OCR results"""
    if img is None:
        return None
    try:
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Resize small images up slightly to improve OCR on small fonts
        h, w = gray.shape[:2]
        if min(h, w) < 300:
            scale = max(1.0, 300.0 / min(h, w))
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Denoise
        denoised = cv2.medianBlur(gray, 3)

        # Adaptive thresholding for variable backgrounds
        try:
            adaptive = cv2.adaptiveThreshold(denoised, 255,
                                             cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                             cv2.THRESH_BINARY, 11, 2)
        except Exception:
            # fallback to Otsu if adaptive threshold fails
            _, adaptive = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Morphological close to join characters that were broken
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel)

        return cleaned
    except Exception as e:
        print(f"Error preprocessing image: {e}")
        # return a reasonable fallback
        return gray if 'gray' in locals() else img

# -------------------------
# OCR extraction helpers
# -------------------------
def _tesseract_texts(img: np.ndarray) -> Tuple[str, float]:
    """
    Run several Tesseract modes and return best text and a confidence estimate (0-1).
    """
    texts = []
    confidences = []

    try:
        # Mode 1: PSM 6 (assumes block of text)
        cfg1 = r'--oem 3 --psm 6'
        t1 = pytesseract.image_to_string(img, config=cfg1)
        texts.append(t1)

        # Mode 2: PSM 7 (single line)
        cfg2 = r'--oem 3 --psm 7'
        t2 = pytesseract.image_to_string(img, config=cfg2)
        texts.append(t2)

        # Mode 3: PSM 11 or 8 (sparse text/single word)
        cfg3 = r'--oem 3 --psm 11'
        t3 = pytesseract.image_to_string(img, config=cfg3)
        texts.append(t3)
    except Exception as e:
        print(f"Tesseract multi-mode OCR failed: {e}")

    # Clean and pick best by length
    texts = [t.strip() for t in texts if t and t.strip()]
    best_text = max(texts, key=len) if texts else ""

    # Try to obtain confidence from image_to_data
    try:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        confs = []
        for c in data.get('conf', []):
            try:
                val = float(c)
                if val >= 0:
                    confs.append(val)
            except Exception:
                continue
        if confs:
            # Tesseract confidences are 0-100; normalize to 0-1
            avg_conf = float(np.mean(confs)) / 100.0
            avg_conf = max(0.0, min(1.0, avg_conf))
            return best_text, avg_conf
    except Exception:
        # ignore if image_to_data not yielding values
        pass

    # Heuristic fallback confidence: proportion of alphabetic words and length
    if best_text:
        words = re.findall(r"[A-Za-z]{2,}", best_text)
        word_count = len(words)
        char_count = len(best_text)
        word_ratio = min(1.0, word_count / max(1, char_count / 5.0))
        heur_conf = min(0.99, 0.2 + 0.8 * word_ratio)
        return best_text, heur_conf

    return "", 0.0

def _easyocr_fallback(img: np.ndarray) -> Tuple[str, float]:
    """If enabled, run EasyOCR as fallback. Returns (text, confidence)"""
    global easyocr_reader
    if not _try_easyocr:
        return "", 0.0
    try:
        if easyocr_reader is None:
            # lazy init
            easyocr_reader = easyocr.Reader(['en'], gpu=False)
        results = easyocr_reader.readtext(img)
        texts = [res[1] for res in results if len(res) >= 2]
        confs = [res[2] for res in results if len(res) >= 3]
        joined = " ".join(texts).strip()
        conf_mean = float(np.mean(confs)) if confs else 0.0
        conf_mean = max(0.0, min(1.0, conf_mean))
        return joined, conf_mean
    except Exception as e:
        print(f"EasyOCR fallback failed: {e}")
        return "", 0.0

def extract_text(img: np.ndarray) -> Tuple[str, float, list]:
    """
    Extract text and return (text, confidence, fallbacks_used_list)
    Will try Tesseract multi-mode, and EasyOCR as fallback (if installed).
    """
    fallbacks = []
    if img is None:
        return "", 0.0, fallbacks

    try:
        t_text, t_conf = _tesseract_texts(img)
        if t_text and t_conf > 0.15:
            return t_text, t_conf, fallbacks

        # if tesseract yields nothing or very low confidence, try EasyOCR
        fallbacks.append("tesseract_low_conf")
        if _try_easyocr:
            e_text, e_conf = _easyocr_fallback(img)
            if e_text and e_conf > t_conf:
                fallbacks.append("easyocr_used")
                return e_text, e_conf, fallbacks

        # last resort: return tesseract best even if low
        return t_text, t_conf, fallbacks
    except Exception as e:
        print(f"Error extracting text with OCR: {e}")
        return "", 0.0, ["ocr_error"]

# -------------------------
# Keyword / Concept helpers (unchanged mostly)
# -------------------------
def extract_keywords(text: str, top_n: int = 15, boost_repeats: bool = True) -> Dict[str, float]:
    """Combine KeyBERT + NLP + repetition + KG boosts. Returns {kw: score}"""
    if not text or not text.strip():
        return {}

    kw_dict = {}
    try:
        if kw_model is not None:
            kw_list = kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),
                stop_words='english',
                top_n=top_n * 2
            )
            kw_dict = {kw[0].lower(): float(kw[1]) for kw in kw_list if kw[0].strip()}
    except Exception as e:
        print(f"KeyBERT extraction failed: {e}")

    try:
        if nlp is not None and text.strip():
            doc = nlp(text[:100000])
            nlp_keywords = [
                token.lemma_.lower() for token in doc
                if token.is_alpha and not token.is_stop
                and token.pos_ in ("NOUN", "PROPN")
                and len(token.lemma_) > 2
            ]
            entities = [ent.text.lower() for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE", "PRODUCT", "EVENT"]]
            for kw in set(nlp_keywords + entities):
                if kw not in kw_dict:
                    kw_dict[kw] = 0.3
    except Exception as e:
        print(f"spaCy processing failed: {e}")

    # Split camelCase / snake_case
    split_keywords = {}
    for kw, score in kw_dict.items():
        try:
            parts = re.split(r'[_\s]', kw)
            final_parts = []
            for part in parts:
                camel_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', part)
                final_parts.extend(camel_parts)
            for p in final_parts:
                p = p.lower().strip()
                if len(p) > 2:
                    split_keywords[p] = max(score, split_keywords.get(p, 0.0))
        except Exception as e:
            print(f"Error splitting keyword {kw}: {e}")
            continue

    kw_dict = split_keywords

    # Boost repeated keywords
    if boost_repeats and text:
        try:
            words = re.findall(r'\b[a-z]{3,}\b', text.lower())
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            for kw in list(kw_dict.keys()):
                if kw in word_counts and word_counts[kw] > 1:
                    kw_dict[kw] += 0.05 * (word_counts[kw] - 1)
        except Exception as e:
            print(f"Repetition boosting failed: {e}")

    # Boost by knowledge graph
    try:
        G = get_graph()
        for kw in list(kw_dict.keys()):
            if kw in G.nodes:
                kw_dict[kw] = min(1.0, kw_dict[kw] + 0.1)
    except Exception as e:
        print(f"Knowledge graph boosting failed: {e}")

    # Sort and return top_n
    try:
        sorted_keywords = dict(sorted(kw_dict.items(), key=lambda x: x[1], reverse=True))
        return dict(list(sorted_keywords.items())[:top_n])
    except Exception as e:
        print(f"Error sorting keywords: {e}")
        return {}

@lru_cache(maxsize=32)
def extract_concepts_v2(text: str, top_n: int = 5):
    if not text or not text.strip():
        return []
    try:
        if kw_model is None:
            return []
        kw_list = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            stop_words='english',
            top_n=top_n * 3
        )
        unique_concepts = []
        for k, score in kw_list:
            key = k.lower().strip()
            if key and key not in unique_concepts and len(key) > 3:
                unique_concepts.append(key)
        return unique_concepts[:top_n]
    except Exception as e:
        print("⚠️ extract_concepts_v2 failed:", e)
        return []

def get_text_embedding_v2(text: str):
    if not text or not text.strip() or embedding_model is None:
        return np.zeros(384)
    try:
        return embedding_model.encode([text])[0]
    except Exception as e:
        print("⚠️ get_text_embedding_v2 failed:", e)
        return np.zeros(384)

# -------------------------
# Main OCR pipeline (public)
# -------------------------
def ocr_pipeline():
    """
    Returns:
    {
      raw_text: str (privacy-redacted, trimmed),
      raw_text_full: str (unredacted full text) - optional,
      keywords: {kw: {"score":float, "count":int}},
      concepts_v2: [...],
      embedding_v2: [...],
      confidence: float (0-1),
      status: "ok"|"partial"|"failed",
      fallbacks: [list of fallbacks used]
    }
    """
    global _last_valid_text, _last_valid_confidence

    try:
        img = capture_screenshot()
        if img is None:
            return {"raw_text": "", "keywords": {}, "concepts_v2": [], "embedding_v2": [], "confidence": 0.0, "status": "failed", "fallbacks": ["capture_failed"]}

        processed_img = preprocess_image(img)
        if processed_img is None:
            return {"raw_text": "", "keywords": {}, "concepts_v2": [], "embedding_v2": [], "confidence": 0.0, "status": "failed", "fallbacks": ["preprocess_failed"]}

        text, conf, fallbacks = extract_text(processed_img)

        # If low confidence, try slight variations of preprocessing (retry logic)
        if conf < 0.25:
            fallbacks.append("low_conf_retry")
            try:
                # try simple Otsu threshold (alternative)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                text2, conf2, fb2 = extract_text(binary)
                if conf2 > conf:
                    text, conf, fallbacks = text2, conf2, fallbacks + fb2 + ["retry_otsu"]
            except Exception:
                pass

        # If still poor, use last valid cached text
        if (not text or conf < 0.15) and _last_valid_text:
            fallbacks.append("use_last_valid_text")
            text = _last_valid_text
            conf = _last_valid_confidence

        # Redact sensitive info before any further processing or storage
        text_redacted = redact_sensitive(text)

        # If no meaningful text
        if not text_redacted or len(re.findall(r"[A-Za-z]{3,}", text_redacted)) < 3:
            status = "partial" if text_redacted else "failed"
        else:
            status = "ok"

        # Extract concepts and embeddings (may be empty if models not loaded)
        concepts = extract_concepts_v2(text_redacted)
        embedding = get_text_embedding_v2(text_redacted)

        # Extract keywords from the (unredacted) text for best results but do not store PII
        keywords_scores = extract_keywords(text)  # keeps original scoring semantics

        # Convert to counts using redacted lowercase text to avoid leaking sensitive tokens
        text_lower = text_redacted.lower() if text_redacted else ""
        keywords_with_counts = {}
        for kw, score in keywords_scores.items():
            try:
                # count occurrences in redacted text to avoid leaking raw emails/passwords
                count = text_lower.count(kw.lower())
                keywords_with_counts[str(kw)] = {"score": float(score), "count": int(count)}
            except Exception as e:
                # If count computation fails, default to 1
                keywords_with_counts[str(kw)] = {"score": float(score), "count": 1}

        # Update last_valid cache if confident
        if conf >= 0.25 and status == "ok":
            _last_valid_text = text
            _last_valid_confidence = conf

        return {
            "raw_text": text_redacted[:1000],  # limit length for safety
            "raw_text_full": text[:4000],     # optional larger raw text kept in memory only (not for DB)
            "keywords": keywords_with_counts,
            "concepts_v2": concepts,
            "embedding_v2": embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding),
            "confidence": float(conf),
            "status": status,
            "fallbacks": fallbacks
        }

    except Exception as e:
        print(f"Error in OCR pipeline: {e}")
        return {"raw_text": "", "keywords": {}, "concepts_v2": [], "embedding_v2": [], "confidence": 0.0, "status": "failed", "fallbacks": ["exception"]}

# Quick test when run directly
if __name__ == "__main__":
    res = ocr_pipeline()
    print("Status:", res.get("status"))
    print("Confidence:", res.get("confidence"))
    print("Fallbacks:", res.get("fallbacks"))
    print("Concepts v2:", res.get("concepts_v2", []))
    print("Keywords count:", len(res.get("keywords", {})))
    print("Text snippet:", res.get("raw_text", "")[:300] + "...")
