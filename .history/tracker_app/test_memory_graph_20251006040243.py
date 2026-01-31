# tests/test_ocr_module.py
import pytest
from unittest.mock import patch, MagicMock
import numpy as np
from core import ocr_module as ocr

# -----------------------------
# Test safe extract_text
# -----------------------------
def test_extract_text_returns_string():
    fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
    with patch("pytesseract.image_to_string", return_value="Sample Text"):
        text = ocr.extract_text(fake_img)
        assert isinstance(text, str)
        assert "Sample Text" in text

# -----------------------------
# Test keyword extraction
# -----------------------------
def test_extract_keywords_basic():
    text = "Machine learning and deep learning models"
    keywords = ocr.extract_keywords(text, top_n=5)
    assert isinstance(keywords, dict)
    assert all(isinstance(k, str) for k in keywords.keys())
    assert all("score" not in k for k in keywords.keys()) == False

# -----------------------------
# Test concept extraction v2
# -----------------------------
def test_extract_concepts_v2_basic():
    text = "Neural networks and convolutional layers"
    concepts = ocr.extract_concepts(text, top_n=3)
    assert isinstance(concepts, list)
    assert all(isinstance(c, str) for c in concepts)
    assert len(concepts) <= 3

def test_extract_concepts_v2_empty():
    concepts = ocr.extract_concepts("")
    assert concepts == []

# -----------------------------
# Test embedding function
# -----------------------------
def test_get_text_embedding_v2_shape():
    emb = ocr.get_text_embedding("Sample text")
    assert isinstance(emb, np.ndarray)
    assert emb.shape[0] == 384

def test_get_text_embedding():
    emb = ocr.get_text_embedding("")
    assert np.array_equal(emb, np.zeros(384))

# -----------------------------
# Test OCR pipeline (mocked)
# -----------------------------
@patch("core.ocr_module.capture_screenshot")
@patch("core.ocr_module.extract_text")
def test_ocr_pipeline(mock_extract_text, mock_capture):
    mock_capture.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_extract_text.return_value = "Test OCR content"
    result = ocr.ocr_pipeline()
    
    assert "raw_text" in result
    assert "keywords" in result
    assert "concepts_v2" in result
    assert "embedding_v2" in result

    assert result["raw_text"] == "Test OCR content"
    assert isinstance(result["keywords"], dict)
    assert isinstance(result["concepts_v2"], list)
    assert isinstance(result["embedding_v2"], list)
