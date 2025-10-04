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

# -----------------------------
# Set tesseract executable path
# -----------------------------
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# -----------------------------
# Initialize models
# -----------------------------
kw_model = KeyBERT()
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
nlp = spacy.load("en_core_web_sm")  # NLP model for extra keywords

# -----------------------------
# Screenshot capture
# -----------------------------
def capture_screenshot():
    """Capture full screen (or specific window later)"""
    with mss() as sct:
        screenshot = sct.grab(sct.monitors[1])
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

# -----------------------------
# Image preprocessing
# -----------------------------
def preprocess_image(img):
    """Grayscale + histogram equalization for OCR"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    return gray

# -----------------------------
# OCR extraction
# -----------------------------
def extract_text(img):
    """Run OCR on preprocessed image"""
    custom_config = r'--oem 3 --psm 6'  # Engine mode + block of text
    text = pytesseract.image_to_string(img, config=custom_config)
    return text

# -----------------------------
# NLP-based keyword extraction
# -----------------------------
def extract_keywords(text, top_n=15):
    """Combine KeyBERT + NLP + knowledge graph prioritization + scores"""
    # 1️⃣ KeyBERT keywords with scores
    kw_list = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2),
                                        stop_words='english', top_n=top_n)
    kw_dict = {kw[0]: kw[1] for kw in kw_list}  # keyword -> score

    # 2️⃣ NLP entity + noun keywords (give a default score)
    doc = nlp(text)
    nlp_keywords = [token.lemma_.lower() for token in doc 
                    if token.is_alpha and not token.is_stop and token.pos_ in ("NOUN","PROPN")]
    entities = [ent.text.lower() for ent in doc.ents]
    
    for kw in nlp_keywords + entities:
        if kw not in kw_dict:
            kw_dict[kw] = 0.3  # default score for NLP keywords

    # 3️⃣ Prioritize keywords in knowledge graph
    G = get_graph()
    for kw in kw_dict:
        if kw in G.nodes:
            kw_dict[kw] += 0.2  # boost for known concepts

    # 4️⃣ Sort by score
    sorted_keywords = dict(sorted(kw_dict.items(), key=lambda x: x[1], reverse=True))

    # Return top_n keywords with scores
    top_keywords = dict(list(sorted_keywords.items())[:top_n])
    return top_keywords

# -----------------------------
# Sentence embeddings
# -----------------------------
def get_embeddings(text):
    """Get sentence embeddings"""
    return embedding_model.encode([text])[0]

# -----------------------------
# Main OCR pipeline
# -----------------------------
def ocr_pipeline():
    img = capture_screenshot()
    processed = preprocess_image(img)
    text = extract_text(processed)
    keywords = extract_keywords(text, top_n=15)  # increased top_n for more coverage
    embedding = get_embeddings(text)
    return {
        "raw_text": text,
        "keywords": keywords,
        "embedding": embedding
    }

# -----------------------------
# Test run
# -----------------------------
if __name__ == "__main__":
    result = ocr_pipeline()
    print("Keywords:", result['keywords'])
    print("Text snippet:", result['raw_text'][:300])
