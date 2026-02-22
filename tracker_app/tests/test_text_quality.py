import pytest
from tracker_app.core.text_quality_validator import (
    validate_and_clean_extraction,
    preprocess_ocr_text,
    is_coherent_text,
    extract_keywords,
    calculate_text_quality_score,
    UI_GARBAGE
)

def test_coherence_detection():
    assert is_coherent_text("Python machine learning algorithm") is True
    assert is_coherent_text("Data science analytics processing") is True
    
    # Needs to either have <15% vowels OR be >3 words of gibberish
    assert is_coherent_text("xvzcvbnmsdfghjkl") is False  # No vowels -> False
    assert is_coherent_text("!@#$%^&*()") is False
    assert is_coherent_text("111222333444555") is False
    assert is_coherent_text("The quick brown fox") is True
    assert is_coherent_text("qwrty psdfg hjklm zxcvb") is False  # No vowels -> False


def test_ocr_preprocessing():
    clean, score = preprocess_ocr_text("  Python  Machine  Learning  ")
    assert "python machine learning" in clean.lower()
    
    clean, score = preprocess_ocr_text("Dat@ Science")
    assert "dat@ science" in clean.lower()
    
    clean, score = preprocess_ocr_text("  AI   is   cool  ")
    assert "ai is cool" in clean.lower()

def test_keyword_extraction():
    assert len(extract_keywords("Python machine learning for data analysis")) >= 3
    assert len(extract_keywords("AI artificial intelligence deep learning")) >= 3
    assert len(extract_keywords("")) == 0
    assert len(extract_keywords("the a an")) == 0

def test_quality_scoring():
    assert calculate_text_quality_score("Machine learning is awesome") >= 0.6
    assert calculate_text_quality_score("asdfghjkl") < 0.3
    assert calculate_text_quality_score("python data science") >= 0.5
    assert calculate_text_quality_score("x" * 1000) < 0.3

def test_complete_validation():
    # Good content
    res = validate_and_clean_extraction("Python programming tutorials")
    assert res['status'] == 'ACCEPTED'
    
    # UI garbage
    res = validate_and_clean_extraction("please wait")
    assert res['status'] in ('REJECTED', 'QUESTIONABLE')
    
    # Spam
    res = validate_and_clean_extraction("click here now")
    assert res['status'] == 'REJECTED'
    
    # Special characters
    res = validate_and_clean_extraction("!@#$%^&*()")
    assert res['status'] == 'REJECTED'
    
    # Error message
    res = validate_and_clean_extraction("unknown error occurred")
    assert res['status'] == 'REJECTED'

def test_ui_garbage_detection():
    garbage_samples = list(UI_GARBAGE)[:10]
    for garbage in garbage_samples:
        result = validate_and_clean_extraction(garbage)
        assert result['is_useful'] is False
        assert result['status'] == 'REJECTED'

def test_ocr_confidence_impact():
    text = "Machine learning"
    
    # High confidence = ACCEPTED
    res_high = validate_and_clean_extraction(text, ocr_confidence=0.9)
    assert res_high['status'] == 'ACCEPTED'
    assert res_high['quality_score'] > 0
    
    # Low confidence = REJECTED
    res_low = validate_and_clean_extraction(text, ocr_confidence=0.1)
    assert res_low['status'] == 'REJECTED'
