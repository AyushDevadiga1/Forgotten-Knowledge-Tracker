# core/ocr_module.py
import cv2
import numpy as np
import pytesseract
import hashlib
from mss import mss
from tracker_app.config import TESSERACT_PATH
import spacy
from tracker_app.core.knowledge_graph import get_graph
from tracker_app.core.keyword_extractor import get_keyword_extractor
from tracker_app.core.text_quality_validator import validate_and_clean_extraction
import re
from functools import lru_cache

# Set tesseract executable path
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Initialize models with error handling
kw_extractor = None
nlp = None

try:
    kw_extractor = get_keyword_extractor()
    print("Lightweight keyword extractor loaded successfully.")
except Exception as e:
    print(f"Error loading keyword extractor: {e}")

try:
    nlp = spacy.load("en_core_web_sm")
    print("spaCy model loaded successfully.")
except Exception as e:
    print(f"Error loading spaCy model: {e}")

# Screenshot deduplication
_last_screenshot_hash = None

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
                from tracker_app.core.roi_detector import capture_active_window, should_skip_window
                img, window_info = capture_active_window()
                
                if img is not None and window_info:
                    # Privacy check
                    if should_skip_window(window_info['title']):
                        print(f"[PRIVACY] Skipped sensitive window: {window_info['title']}")
                        return None
                    
                    # Deduplication check
                    img_hash = hashlib.md5(img.tobytes()).hexdigest()
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
            
            # Calculate hash for deduplication
            img_hash = hashlib.md5(img.tobytes()).hexdigest()
            
            # Skip if same as last screenshot
            if img_hash == _last_screenshot_hash:
                return None
            
            _last_screenshot_hash = img_hash
            
            # Convert BGRA to BGR if needed
            if img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                
            return img
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
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
        print(f"Error preprocessing image: {e}")
        return gray if 'gray' in locals() else img

def extract_text(img):
    """Extract text from image using optimized OCR strategy"""
    if img is None:
        return ""
        
    try:
        # Use ONLY PSM 6 (default) - removed PSM 7 and 8 for performance
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?;:()[]{}@#$%&*+-/=<> '
        text = pytesseract.image_to_string(img, config=custom_config)
        
        return text.strip() if text else ""
        
    except Exception as e:
        print(f"Error extracting text with OCR: {e}")
        return ""

def extract_keywords(text, top_n=15, boost_repeats=True):
    """Extract keywords with quality validation and privacy filtering"""
    if not text or len(text.strip()) < 10:
        return {}
    
    # Privacy filter FIRST
    try:
        from tracker_app.core.privacy_filter import sanitize_text_for_storage
        sanitized = sanitize_text_for_storage(text)
        
        if not sanitized['safe_to_store']:
            print("[PRIVACY] Text rejected due to sensitive content")
            return {}
        
        # Use sanitized text
        text = sanitized['text']
        
        if sanitized['is_sanitized']:
            print(f"[PRIVACY] Redacted {sanitized['num_redactions']} sensitive items")
    except ImportError:
        pass  # Privacy filter not available
    
    # Quality validation
    validation = validate_and_clean_extraction(text)
    
    # Reject garbage immediately
    if not validation['is_useful']:
        print(f"[FILTERED] Rejected text: {validation['reason']}")
        return {}
    
    # Use cleaned text for extraction
    clean_text = validation['cleaned_text']
    concepts = {}
    
    try:
        # TF-IDF extraction on VALIDATED and SANITIZED text
        if kw_extractor:
            keywords = kw_extractor.extract_keywords(clean_text, top_n=10)
            for kw, score in keywords:
                # Additional filter: skip single-char and UI garbage
                if len(kw) > 2 and kw.lower() not in {'the', 'and', 'for', 'with'}:
                    concepts[kw] = score * 0.8
    except Exception as e:
        print(f"Keyword extraction failed: {e}")

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
            
            # Add to dictionary with moderate scores
            for kw in set(nlp_keywords + entities):
                if kw not in kw_dict:
                    kw_dict[kw] = 0.3
    except Exception as e:
        print(f"spaCy processing failed: {e}")

    # 3️⃣ Split camelCase / snake_case
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
                if len(p) > 2:  # Only keep meaningful parts
                    split_keywords[p] = max(score, split_keywords.get(p, 0.0))
        except Exception as e:
            print(f"Error splitting keyword {kw}: {e}")
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
            print(f"Repetition boosting failed: {e}")

    # 5️⃣ Boost keywords existing in knowledge graph
    try:
        G = get_graph()
        for kw in list(kw_dict.keys()):
            if kw in G.nodes:
                kw_dict[kw] = min(1.0, kw_dict[kw] + 0.1)  # Small consistent boost
    except Exception as e:
        print(f"Knowledge graph boosting failed: {e}")

    # 6️ Sort by score and return top_n
    try:
        sorted_keywords = dict(sorted(kw_dict.items(), key=lambda x: x[1], reverse=True))
        return dict(list(sorted_keywords.items())[:top_n])
    except Exception as e:
        print(f"Error sorting keywords: {e}")
        return {}

@lru_cache(maxsize=32)
def extract_concepts_v2(text, top_n=5):
    """Extract concepts from OCR text using lightweight keyword extraction"""
    if not text or len(text.strip()) < 5:
        return []
    
    try:
        # Use TF-IDF for concept extraction with broader range
        if kw_extractor:
            keywords = kw_extractor.extract_keywords(text, top_n=20)
            return [kw for kw, score in keywords if score > 0.1][:top_n]
        return []
    except Exception as e:
        print(f"[WARN] extract_concepts_v2 failed: {e}")
        return []


def get_text_embedding_v2(text):
    """Compute sentence embeddings for semantic search"""
    if not text or not text.strip() or embedding_model is None:
        return np.zeros(384)  # Default embedding size for all-MiniLM-L6-v2
        
    try:
        return embedding_model.encode([text])[0]
    except Exception as e:
        print("[WARN] get_text_embedding_v2 failed:", e)
        return np.zeros(384)

def ocr_pipeline():
    """Complete OCR processing pipeline with error handling"""
    try:
        # Capture screenshot
        img = capture_screenshot()
        if img is None:
            return {"keywords": {}, "concepts_v2": [], "embedding_v2": [], "raw_text": ""}

        # Preprocess image
        processed_img = preprocess_image(img)
        if processed_img is None:
            return {"keywords": {}, "concepts_v2": [], "embedding_v2": [], "raw_text": ""}

        # Extract text
        text = extract_text(processed_img)
        if not text.strip():
            return {"keywords": {}, "concepts_v2": [], "embedding_v2": [], "raw_text": ""}

        # Extract concepts and embeddings
        concepts = extract_concepts_v2(text)
        embedding = get_text_embedding_v2(text)

        # Extract keywords with scores
        keywords_with_scores = extract_keywords(text, top_n=15)
        
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
                print(f"Error processing keyword {kw}: {e}")
                continue

        return {
            "raw_text": str(text)[:500],  # Limit text length
            "keywords": keywords_with_counts,
            "concepts_v2": concepts,
            "embedding_v2": embedding.tolist()
        }
        
    except Exception as e:
        print(f"Error in OCR pipeline: {e}")
        return {"keywords": {}, "concepts_v2": [], "embedding_v2": [], "raw_text": ""}

if __name__ == "__main__":
    result = ocr_pipeline()
    print("Concepts v2:", result.get('concepts_v2', []))
    print("Keywords count:", len(result.get('keywords', {})))
    print("Text snippet:", result.get('raw_text', '')[:200] + "...")