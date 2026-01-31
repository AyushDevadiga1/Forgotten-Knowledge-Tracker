import cv2, numpy as np, pytesseract, re
from mss import mss
from config import TESSERACT_PATH
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
import spacy
from core.knowledge_graph import get_graph

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
kw_model = KeyBERT()
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
nlp = spacy.load("en_core_web_sm")

def capture_screenshot():
    with mss() as sct:
        shot = sct.grab(sct.monitors[1])
        img = cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR)
        return img

def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.equalizeHist(gray)

def extract_text(img):
    return pytesseract.image_to_string(img, config=r'--oem 3 --psm 6')

def extract_concepts(text, top_n=5):
    """Extract high-level revision topics using KeyBERT + title heuristics."""
    lines = [l.strip() for l in text.split('\n') if 3 < len(l.split()) < 10]
    title_candidates = [l for l in lines if any(w[0].isupper() for w in l.split())]
    kw_list = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,3),
                                        stop_words='english', top_n=top_n*3)
    all_cands = {kw:score for kw,score in kw_list}
    for t in title_candidates:
        all_cands[t] = all_cands.get(t,0.4)+0.6
    text_lower = text.lower()
    for k in list(all_cands.keys()):
        freq = text_lower.count(k.lower())
        all_cands[k] *= (1 + 0.1*freq)
    G = get_graph()
    for k in list(all_cands.keys()):
        if k in G.nodes:
            all_cands[k] += 0.2
    sorted_items = sorted(all_cands.items(), key=lambda x:x[1], reverse=True)
    return [x[0] for x in sorted_items[:top_n]]

def get_embeddings(text): 
    return embedding_model.encode([text])[0]

def ocr_pipeline():
    img = preprocess_image(capture_screenshot())
    text = extract_text(img)
    concepts = extract_concepts(text)
    embedding = get_embeddings(text)
    return {"raw_text": text, "concepts": concepts, "embedding": embedding}

if __name__ == "__main__":
    print(ocr_pipeline())
