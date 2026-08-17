"""OCR pipeline: active-window capture, Tesseract extraction, keyword/concept extraction."""
import cv2
import numpy as np
import pytesseract
import hashlib
from mss import mss
from tracker_app.config import TESSERACT_PATH, OCR_MIN_WORD_CONFIDENCE
import spacy
import logging
from tracker_app.tracking.knowledge_graph import get_graph
from tracker_app.tracking.keyword_extractor import get_keyword_extractor
from tracker_app.learning.text_quality_validator import validate_and_clean_extraction
from tracker_app.tracking.privacy_filter import (
    sanitize_text_for_storage, is_sensitive_window, strip_redaction_markers,
    filter_sensitive_keywords,
)
import re
from functools import lru_cache

logger = logging.getLogger("OCRModule")

# Set tesseract executable path
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Startup sanity-check: warn loudly if Tesseract isn't where we expect it.
import os as _os
if TESSERACT_PATH.lower() != "tesseract" and not _os.path.exists(TESSERACT_PATH):
    logger.warning(
        f"[OCR] Tesseract binary NOT found at '{TESSERACT_PATH}'. "
        "OCR will silently return empty text. Run setup.py or set TESSERACT_PATH in .env."
    )
elif TESSERACT_PATH.lower() == "tesseract":
    import shutil as _shutil
    if not _shutil.which("tesseract"):
        logger.warning(
            "[OCR] Tesseract is not on PATH. OCR will silently return empty text. "
            "Run setup.py or set TESSERACT_PATH in .env."
        )

# Initialize models with error handling
kw_extractor = None
nlp = None

try:
    kw_extractor = get_keyword_extractor()
    logger.info("Keyword extractor loaded.")
except Exception as e:
    logger.warning(f"Keyword extractor load failed: {e}")

try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("spaCy model loaded.")
except Exception as e:
    logger.warning(f"spaCy load failed: {e}")

# Screenshot deduplication
_last_screenshot_hash = None

# ----------------------------
# Screenshot hashing helpers
# ----------------------------

def should_skip_window(title: str) -> bool:
    """Return True if the window title suggests sensitive/private content."""
    return is_sensitive_window(title)

def capture_active_window():
    """
    Attempt to capture only the active (foreground) window region.
    Returns (image_array, window_info_dict) or (None, None) on failure.
    """
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or ""
        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            return None, None
        with mss() as sct:
            monitor = {"left": left, "top": top, "width": width, "height": height}
            img = np.array(sct.grab(monitor))
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img, {"title": title, "rect": rect}
    except ImportError:
        return None, None  # Non-Windows: fallback to full screen
    except Exception as e:
        logger.debug(f"capture_active_window failed: {e}")
        return None, None

def capture_screenshot(use_roi=True):
    """
    Capture screenshot with deduplication and optional ROI detection.
    
    Args:
        use_roi: If True, capture only active window (faster, more private)
    """
    global _last_screenshot_hash
    
    try:
        # Try ROI capture first (active window only)
        if use_roi:
            try:
                img, window_info = capture_active_window()
                
                if img is not None and window_info:
                    # Privacy check
                    if should_skip_window(window_info['title']):
                        logger.warning(f"[PRIVACY] Skipped sensitive window: {window_info['title']}")
                        return None
                    
                    # Deduplication check — hash a small thumbnail (~100x faster than full frame)
                    thumb = cv2.resize(img, (192, 108)) if img is not None else img
                    img_hash = hashlib.md5(thumb.tobytes()).hexdigest()
                    if img_hash == _last_screenshot_hash:
                        return None
                    
                    _last_screenshot_hash = img_hash
                    return img
            except ImportError:
                pass  # Fall back to full screen
        
        # Fallback: Full screen capture
        with mss() as sct:
            monitor = sct.monitors[1]
            img = np.array(sct.grab(monitor))
            
            # Calculate hash for deduplication — use thumbnail for speed
            thumb = cv2.resize(img, (192, 108))
            img_hash = hashlib.md5(thumb.tobytes()).hexdigest()
            
            # Skip if same as last screenshot
            if img_hash == _last_screenshot_hash:
                return None
            
            _last_screenshot_hash = img_hash
            
            # Convert BGRA to BGR if needed
            if img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                
            return img
    except Exception as e:
        logger.warning(f"Error capturing screenshot: {e}")
        return None

def preprocess_image(img):
    """Preprocess image for better OCR results"""
    if img is None:
        return None
        
    try:
        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
            
        # Apply preprocessing for better OCR
        # 1. Noise reduction
        denoised = cv2.medianBlur(gray, 3)
        
        # 2. Thresholding to binary
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 3. Morphological operations to clean up text
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
        
    except Exception as e:
        logger.warning(f"Error preprocessing image: {e}")
        return gray if 'gray' in locals() else img

def extract_text(img, min_confidence: int = None):
    """Extract text from image using optimized OCR strategy.

    Uses per-word confidence (image_to_data) and drops words below
    OCR_MIN_WORD_CONFIDENCE. Tesseract scores misreads of UI chrome /
    overlapping windows very low (often 0.0) while readable study content
    scores 50-95 — so this filters OCR garble at the source instead of
    letting every misread try the plausibility gate downstream.
    """
    if img is None:
        return ""

    if min_confidence is None:
        min_confidence = OCR_MIN_WORD_CONFIDENCE

    try:
        # Use ONLY PSM 6 (default) - removed PSM 7 and 8 for performance
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?;:()[]{}@#$%&*+-/=<> '
        data = pytesseract.image_to_data(
            img, config=custom_config, output_type=pytesseract.Output.DICT
        )

        # Reconstruct text line-by-line, keeping only confident words.
        # Key = (block, paragraph, line) so reading order survives sorting.
        lines: dict = {}
        n = len(data.get('text', []))
        for i in range(n):
            word = (data['text'][i] or '').strip()
            if not word:
                continue
            try:
                conf = float(data['conf'][i])
            except (TypeError, ValueError):
                continue
            if conf < min_confidence:
                continue
            key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
            lines.setdefault(key, []).append(word)

        if not lines:
            return ""

        pieces = [' '.join(lines[key]) for key in sorted(lines.keys())]
        return '\n'.join(pieces).strip()

    except Exception as e:
        logger.warning(f"Error extracting text with OCR: {e}")
        return ""

def extract_keywords(text, top_n=15, boost_repeats=True, graph=None):
    """Extract keywords with quality validation and privacy filtering.

    graph: optional preloaded knowledge graph. When provided the node-boost
    lookup uses it directly instead of calling get_graph() (which may
    trigger a DB sync) from the OCR worker thread (M-4).
    """
    if not text or len(text.strip()) < 10:
        return {}
    
    # Privacy filter FIRST (mandatory structural gate — imported at module load,
    # so this can never silently disappear)
    sanitized = sanitize_text_for_storage(text)

    if not sanitized['safe_to_store']:
        logger.warning("[PRIVACY] Text rejected due to sensitive content")
        return {}

    # Use sanitized text
    text = sanitized['text']

    if sanitized['is_sanitized']:
        logger.warning(f"[PRIVACY] Redacted {sanitized['num_redactions']} sensitive items")

    # Strip [REDACTED:TYPE] markers so 'email'/'phone'/'password' etc. can
    # never become extracted concepts (they are marker noise, not study terms).
    text = strip_redaction_markers(text)
    
    # Quality validation
    validation = validate_and_clean_extraction(text)
    
    # Reject garbage immediately
    if not validation['is_useful']:
        logger.info(f"[FILTERED] Rejected text: {validation['reason']}")
        return {}
    
    # Use cleaned text for extraction
    clean_text = validation['cleaned_text']
    kw_dict = {}  # unified keyword dict used by all extraction steps below
    
    try:
        # TF-IDF extraction on VALIDATED and SANITIZED text
        if kw_extractor:
            keywords = kw_extractor.extract_keywords(clean_text, top_n=10)
            for kw, score in keywords:
                # Additional filter: skip single-char and UI garbage
                if len(kw) > 2 and kw.lower() not in {'the', 'and', 'for', 'with'}:
                    kw_dict[kw] = score * 0.8
    except Exception as e:
        logger.warning(f"Keyword extraction failed: {e}")

    try:
        # 2️⃣ NLP nouns/proper nouns & entities (if available)
        if nlp is not None and text.strip():
            doc = nlp(text[:100000])  # Limit text length for performance
            
            # Extract nouns and proper nouns
            nlp_keywords = [
                token.lemma_.lower() for token in doc
                if token.is_alpha and not token.is_stop 
                and token.pos_ in ("NOUN", "PROPN")
                and len(token.lemma_) > 2
            ]
            
            # Extract named entities
            entities = [ent.text.lower() for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE", "PRODUCT", "EVENT"]]
            
            # Add to kw_dict with moderate scores
            for kw in set(nlp_keywords + entities):
                if kw not in kw_dict:
                    kw_dict[kw] = 0.3
    except Exception as e:
        logger.warning(f"spaCy processing failed: {e}")

    # 3️⃣ Split camelCase / snake_case — but keep multi-word phrases intact:
    # 'calvin cycle' is a better concept than 'calvin' + 'cycle', and the old
    # unconditional split was destroying every YAKE two-word keyword.
    split_keywords = {}
    for kw, score in kw_dict.items():
        try:
            if ' ' in kw:
                split_keywords[kw] = max(score, split_keywords.get(kw, 0.0))
                continue
            split_keywords[kw.lower()] = max(score, split_keywords.get(kw.lower(), 0.0))
            parts = re.split(r'[_]', kw)
            final_parts = []
            for part in parts:
                camel_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', part)
                final_parts.extend(camel_parts)
            
            for p in final_parts:
                p = p.lower().strip()
                if len(p) > 2:  # Only keep meaningful parts
                    split_keywords[p] = max(score, split_keywords.get(p, 0.0))
        except Exception as e:
            logger.warning(f"Error splitting keyword {kw}: {e}")
            continue
            
    kw_dict = split_keywords

    # 4️⃣ Boost repeated keywords in text
    if boost_repeats and text:
        try:
            words = re.findall(r'\b[a-z]{3,}\b', text.lower())  # Words of 3+ letters
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            for kw in list(kw_dict.keys()):
                if kw in word_counts and word_counts[kw] > 1:
                    kw_dict[kw] += 0.05 * (word_counts[kw] - 1)  # Small boost per repetition
        except Exception as e:
            logger.warning(f"Repetition boosting failed: {e}")

    # 5️⃣ Boost keywords existing in knowledge graph
    try:
        if graph is None:
            graph = get_graph()
        for kw in list(kw_dict.keys()):
            if kw in graph.nodes:
                kw_dict[kw] = min(1.0, kw_dict[kw] + 0.1)  # Small consistent boost
    except Exception as e:
        logger.warning(f"Knowledge graph boosting failed: {e}")

    # 6️ Sort by score and return top_n
    try:
        sorted_keywords = dict(sorted(kw_dict.items(), key=lambda x: x[1], reverse=True))
        top = dict(list(sorted_keywords.items())[:top_n])
        # Drop any keyword that is itself sensitive data or marker noise.
        return filter_sensitive_keywords(top)
    except Exception as e:
        logger.warning(f"Error sorting keywords: {e}")
        return {}

@lru_cache(maxsize=32)
def extract_concepts_v2(text, top_n=5):
    """Extract concepts from OCR text using lightweight keyword extraction"""
    if not text or len(text.strip()) < 5:
        return []
    
    # Privacy gate on the concept path too (defense-in-depth — the pipeline
    # result currently only uses 'keywords', but this must never leak raw PII).
    sanitized = sanitize_text_for_storage(text)
    if not sanitized['safe_to_store']:
        return []
    clean = strip_redaction_markers(sanitized['text'])

    try:
        if kw_extractor:
            keywords = kw_extractor.extract_keywords(clean, top_n=20)
            return [kw for kw, score in filter_sensitive_keywords(
                        dict(keywords)).items() if score > 0.1][:top_n]
        return []
    except Exception as e:
        logger.warning(f"extract_concepts_v2 failed: {e}")
        return []



def ocr_pipeline():
    """Complete OCR processing pipeline with error handling"""
    try:
        # Capture screenshot
        img = capture_screenshot()
        if img is None:
            return {"keywords": {}, "concepts_v2": [], "raw_text": ""}

        # Preprocess image
        processed_img = preprocess_image(img)
        if processed_img is None:
            return {"keywords": {}, "concepts_v2": [], "raw_text": ""}

        # Extract text
        text = extract_text(processed_img)
        if not text.strip():
            return {"keywords": {}, "concepts_v2": [], "raw_text": ""}

        # Extract concepts and embeddings
        concepts = extract_concepts_v2(text)

        # Extract keywords with scores (graph loaded once per pipeline, M-4)
        G = get_graph()
        keywords_with_scores = extract_keywords(text, top_n=15, graph=G)
        
        # Convert to proper format with counts
        text_lower = text.lower()
        keywords_with_counts = {}
        
        for kw, score in keywords_with_scores.items():
            try:
                count = text_lower.count(kw.lower())
                keywords_with_counts[str(kw)] = {
                    "score": float(score),
                    "count": int(count)
                }
            except Exception as e:
                logger.warning(f"Error processing keyword {kw}: {e}")
                continue

        return {
            "raw_text": str(text)[:500],  # Limit text length
            "keywords": keywords_with_counts,
            "concepts_v2": concepts,
        }
        
    except Exception as e:
        logger.warning(f"Error in OCR pipeline: {e}")
        return {"keywords": {}, "concepts_v2": [], "raw_text": ""}

if __name__ == "__main__":
    result = ocr_pipeline()
    print("Concepts v2:", result.get('concepts_v2', []))
    print("Keywords count:", len(result.get('keywords', {})))
    print("Text snippet:", result.get('raw_text', '')[:200] + "...")