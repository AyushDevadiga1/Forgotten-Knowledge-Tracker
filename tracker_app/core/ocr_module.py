# core/ocr_module.py
import cv2
import numpy as np
import pytesseract
from mss import mss
from tracker_app.config import TESSERACT_PATH
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
import spacy
from tracker_app.core.knowledge_graph import get_graph
import re
from functools import lru_cache

# Set tesseract executable path
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Initialize models with error handling
kw_model = None
embedding_model = None
nlp = None

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

def capture_screenshot():
    """Capture screenshot safely"""
    try:
        with mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)
            
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
    """Extract text from image with multiple OCR strategies"""
    if img is None:
        return ""
        
    try:
        # Strategy 1: Default OCR
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?;:()[]{}@#$%&*+-/=<> '
        text1 = pytesseract.image_to_string(img, config=custom_config)
        
        # Strategy 2: Single text line mode (for titles/headings)
        custom_config2 = r'--oem 3 --psm 7'
        text2 = pytesseract.image_to_string(img, config=custom_config2)
        
        # Strategy 3: Single word mode
        custom_config3 = r'--oem 3 --psm 8'
        text3 = pytesseract.image_to_string(img, config=custom_config3)
        
        # Combine strategies, preferring longer, cleaner text
        texts = [text1, text2, text3]
        texts = [t.strip() for t in texts if t and t.strip()]
        
        if not texts:
            return ""
            
        # Return the longest non-empty text
        return max(texts, key=len)
        
    except Exception as e:
        print(f"Error extracting text with OCR: {e}")
        return ""

def extract_keywords(text, top_n=15, boost_repeats=True):
    """Combine KeyBERT + NLP + repetition + KG boosts"""
    if not text or not text.strip():
        return {}
    
    kw_dict = {}

    try:
        # 1️⃣ KeyBERT extraction (if available)
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
    """Extract high-level semantic concepts for topic headings"""
    if not text or not text.strip():
        return []

    try:
        if kw_model is None:
            return []
            
        # Use KeyBERT for concept extraction with broader range
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
        print("[WARN] extract_concepts_v2 failed:", e)
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