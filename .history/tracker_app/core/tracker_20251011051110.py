# core/ocr_module.py
"""
High-Precision OCR + Keyword Extraction (IEEE-Ready)
----------------------------------------------------
- Captures screen text using PaddleOCR
- Cleans and extracts only relevant nouns/proper nouns
- Deduplicates and normalizes keywords
- Filters based on knowledge graph concepts (if loaded)
"""

import numpy as np
from PIL import ImageGrab
from paddleocr import PaddleOCR
from keybert import KeyBERT
import spacy
import logging
import os
from core.knowledge_graph import get_graph

# -----------------------------
# Logger setup
# -----------------------------
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/ocr_module.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -----------------------------
# Load models
# -----------------------------
ocr_model = PaddleOCR(use_angle_cls=True, lang='en')
kw_model = KeyBERT()
nlp = spacy.load("en_core_web_sm")

# -----------------------------
# OCR capture
# -----------------------------
def capture_text_from_screen() -> str:
    try:
        img = np.array(ImageGrab.grab())
        result = ocr_model.ocr(img, cls=True)
        text = " ".join([line[1][0] for page in result for line in page])
        logging.info("Captured text from screen")
        return text
    except Exception as e:
        logging.error(f"OCR capture failed: {e}")
        return ""

# -----------------------------
# Clean keyword extraction
# -----------------------------
def extract_keywords(text: str, top_n=15) -> dict:
    """
    Extracts only relevant, clean keywords from OCR text
    """
    keywords = {}
    if not text:
        return keywords

    try:
        doc = nlp(text)
        # Only NOUNs and PROPNs
        candidate_words = {token.text.lower() for token in doc if token.pos_ in {"NOUN", "PROPN"}}

        raw_keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words='english',
            top_n=top_n
        )

        # Deduplicate & normalize
        seen = set()
        for kw, score in raw_keywords:
            kw_norm = kw.lower()
            if kw_norm not in seen and any(w.lower() in candidate_words for w in kw.split()):
                keywords[kw] = {"score": float(score), "count": 1}
                seen.add(kw_norm)

        # Optional: filter based on existing knowledge graph
        G = get_graph()
        if G and G.number_of_nodes() > 0:
            keywords = {k: v for k, v in keywords.items() if k.lower() in (node.lower() for node in G.nodes)}

        logging.info("Extracted %d clean keywords", len(keywords))
        return keywords
    except Exception as e:
        logging.error(f"Keyword extraction failed: {e}")
        return {}

# -----------------------------
# Main OCR pipeline
# -----------------------------
def ocr_pipeline() -> dict:
    text = capture_text_from_screen()
    keywords = extract_keywords(text)
    return {"keywords": keywords}

# -----------------------------
# Self-test
# -----------------------------
if __name__ == "__main__":
    result = ocr_pipeline()
    print("Top keywords:", list(result["keywords"].keys()))
