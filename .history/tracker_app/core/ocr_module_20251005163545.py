# ==========================================================
# core/ocr_module.py (v2 upgrade)
# ==========================================================

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
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------
# Set tesseract executable path
# -----------------------------
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# -----------------------------
# Initialize models
# -----------------------------
kw_model = KeyBERT()
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
nlp = spacy.load("en_core_web_sm")

# -----------------------------
# Screenshot capture
# -----------------------------
def capture_screenshot():
    with mss() as sct:
        screenshot = sct.grab(sct.monitors[1])
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

# -----------------------------
# Image preprocessing
# -----------------------------
def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    return gray

# -----------------------------
# OCR extraction
# -----------------------------
def extract_text(img):
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(img, config=custom_config)
    return text

# -----------------------------
# Old keyword extraction (preserved)
# -----------------------------
def extract_keywords(text, top_n=15, boost_repeats=True):
    """Original KeyBERT + NLP + repetition + KG boosts"""
    
    kw_list = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2),
                                        stop_words='english', top_n=top_n*2)
    kw_dict = {kw[0].lower(): {"score": kw[1], "count": 0} for kw in kw_list}

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
def get_embeddings(text):
    return embedding_model.encode([text])[0]

# ==========================================================
# ------------------- Upgraded v2 functions ----------------
# ==========================================================

def clean_keywords(keywords):
    """Remove short, numeric, and noise words"""
    noise_patterns = ["py", "csv", "logs", "_", ">", "|", ":", ".", "test", "main"]
    clean = [kw for kw in keywords if len(kw) > 2 and not any(n in kw for n in noise_patterns)]
    return clean

def cluster_keywords_to_topics(keywords, threshold=0.65):
    """Cluster keywords into semantic topics using embeddings"""
    if not keywords:
        return []

    kw_embeddings = embedding_model.encode(keywords)
    clustered = []
    used = set()

    for i, kw_i in enumerate(keywords):
        if i in used:
            continue
        cluster = [kw_i]
        used.add(i)
        for j, kw_j in enumerate(keywords[i+1:], start=i+1):
            if j in used:
                continue
            sim = cosine_similarity([kw_embeddings[i]], [kw_embeddings[j]])[0][0]
            if sim > threshold:
                cluster.append(kw_j)
                used.add(j)
        topic_name = " ".join(cluster)
        clustered.append(topic_name)
    return clustered

def compute_topic_scores(topics, text, KG=None):
    """Assign importance scores based on frequency, KG presence, and length"""
    scores = {}
    text_lower = text.lower()
    for topic in topics:
        freq = sum(text_lower.count(kw) for kw in topic.split())
        kg_bonus = 0.2 if KG else 0
        scores[topic] = freq + kg_bonus + len(topic.split())*0.1
    return scores

# -----------------------------
# Main OCR pipeline v2
# -----------------------------
def ocr_pipeline_v2():
    img = capture_screenshot()
    processed = preprocess_image(img)
    text = extract_text(processed)

    # Old keywords intact
    keywords_old = extract_keywords(text, top_n=15)

    # Clean & generate v2 topics
    keywords_list = clean_keywords(list(keywords_old.keys()))
    concepts_v2 = cluster_keywords_to_topics(keywords_list)
    KG = get_graph()
    topic_scores = compute_topic_scores(concepts_v2, text, KG=KG)

    embedding_v2 = get_embeddings(text)

    return {
        "raw_text": str(text),
        "keywords": keywords_old,       # old pipeline
        "concepts_v2": concepts_v2,    # semantic topics
        "embedding_v2": embedding_v2,  # sentence embedding
        "topic_scores": topic_scores   # optional weights for reminders
    }

# -----------------------------
# Test run
# -----------------------------
if __name__ == "__main__":
    from pprint import pprint
    result = ocr_pipeline_v2()
    print("📄 Raw Text Snippet (first 500 chars):")
    print(result['raw_text'][:500])
    print("\n🔑 Old Keywords:")
    pprint(result['keywords'])
    print("\n💡 Concepts v2 (topics):")
    pprint(result['concepts_v2'])
    print("\n📊 Topic Scores:")
    pprint(result['topic_scores'])
    print("\n✅ OCR v2 Test Completed.")
