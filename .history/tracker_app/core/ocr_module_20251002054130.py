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
def extract_keywords(text, top_n=15, boost_repeats=True):
    """Extract keywords with KeyBERT, NLP, KG boost, and repetition scoring."""
    
    # 1️⃣ KeyBERT extraction
    kw_list = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2),
                                        stop_words='english', top_n=top_n*2)  # extract extra
    kw_dict = {kw[0].lower(): kw[1] for kw in kw_list}

    # 2️⃣ NLP entities/nouns
    doc = nlp(text)
    nlp_keywords = [token.lemma_.lower() for token in doc
                    if token.is_alpha and not token.is_stop and token.pos_ in ("NOUN","PROPN")]
    entities = [ent.text.lower() for ent in doc.ents]

    for kw in nlp_keywords + entities:
        if kw not in kw_dict:
            kw_dict[kw] = 0.3

    # 3️⃣ Split snake_case / camelCase
    import re
    split_keywords = {}
    for kw, score in kw_dict.items():
        parts = re.split(r'[_\s]', kw)
        final_parts = []
        for part in parts:
            camel_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', part)
            final_parts.extend(camel_parts)
        for p in final_parts:
            p = p.lower()
            if len(p) > 2:  # filter very short tokens
                split_keywords[p] = max(score, split_keywords.get(p, 0.0))
    kw_dict = split_keywords

    # 4️⃣ Boost repeated keywords
    if boost_repeats:
        word_counts = {}
        for word in text.lower().split():
            word_counts[word] = word_counts.get(word, 0) + 1
        for kw in kw_dict:
            if kw in word_counts and word_counts[kw] > 1:
                kw_dict[kw] += 0.1 * (word_counts[kw]-1)  # small boost per repetition

    # 5️⃣ Knowledge Graph boost
    G = get_graph()
    for kw in kw_dict:
        if kw in G.nodes:
            kw_dict[kw] += 0.2

    # 6️⃣ Sort and return top_n
    sorted_keywords = dict(sorted(kw_dict.items(), key=lambda x: x[1], reverse=True))
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
    keywords_with_scores = extract_keywords(text, top_n=15)
    embedding = get_embeddings(text)
    return {
        "raw_text": text,
        "keywords": keywords_with_scores,  # now with scores
        "embedding": embedding
    }

# -----------------------------
# Test run
# -----------------------------
if __name__ == "__main__":
    result = ocr_pipeline()
    print("Keywords:", result['keywords'])
    print("Text snippet:", result['raw_text'][:300])
