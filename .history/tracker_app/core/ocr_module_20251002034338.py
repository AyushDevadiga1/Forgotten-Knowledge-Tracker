#core/ocr.py
import cv2
import numpy as np
import pytesseract
from mss import mss
from config import TESSERACT_PATH
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer

# Set tesseract executable path
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Initialize models
kw_model = KeyBERT()
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def capture_screenshot():
    """Capture full screen (or specific window later)"""
    with mss() as sct:
        screenshot = sct.grab(sct.monitors[1])
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

def preprocess_image(img):
    """Grayscale + contrast for OCR"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    return gray

def extract_text(img):
    """Run OCR on preprocessed image"""
    text = pytesseract.image_to_string(img)
    return text

def extract_keywords(text, top_n=5):
    """Extract top study keywords using KeyBERT"""
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2), stop_words='english', top_n=top_n)
    return [kw[0] for kw in keywords]

def get_embeddings(text):
    """Get sentence embeddings"""
    return embedding_model.encode([text])[0]

def ocr_pipeline():
    img = capture_screenshot()
    processed = preprocess_image(img)
    text = extract_text(processed)
    keywords = extract_keywords(text)
    embedding = get_embeddings(text)
    return {
        "raw_text": text,
        "keywords": keywords,
        "embedding": embedding
    }

if __name__ == "__main__":
    result = ocr_pipeline()
    print("Keywords:", result['keywords'])
    print("Text snippet:", result['raw_text'][:200])
