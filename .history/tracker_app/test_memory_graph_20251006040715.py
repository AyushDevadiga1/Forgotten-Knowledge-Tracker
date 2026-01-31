# test_memory_graph.py
import logging
from core.ocr_module import ocr_pipeline, get_text_embedding_v2

# -----------------------------
# Configure logging
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logging.getLogger('sentence_transformers').setLevel(logging.WARNING)  # suppress verbose info

# -----------------------------
# Test the OCR + concept extraction pipeline
# -----------------------------
if __name__ == "__main__":
    logging.info("Starting OCR & Memory Graph Test...")

    # Run OCR pipeline (captures screenshot, extracts text & concepts)
    result = ocr_pipeline()
    
    logging.info(f"Concepts v2: {result.get('concepts_v2')}")
    logging.info(f"Keywords (old pipeline): {result['keywords']}")
    logging.info(f"Text snippet: {result['raw_text'][:300]}")

    # Test embedding function separately
    sample_text = "Linear regression and gradient descent are key machine learning concepts."
    embedding = get_text_embedding(sample_text)
    logging.info(f"Embedding vector length: {len(embedding)}")
