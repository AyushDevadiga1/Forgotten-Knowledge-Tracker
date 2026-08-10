import pytest
from tracker_app.learning.text_quality_validator import (
    validate_and_clean_extraction,
    preprocess_ocr_text,
    is_coherent_text,
    extract_keywords,
    calculate_text_quality_score,
    is_plausible_concept,
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

def test_plausible_concept_accepts_real_keywords():
    assert is_plausible_concept("neural network") is True
    assert is_plausible_concept("mitochondria") is True
    assert is_plausible_concept("gradient descent") is True
    assert is_plausible_concept("atp") is True
    assert is_plausible_concept("dna replication") is True
    assert is_plausible_concept("SQL") is True
    assert is_plausible_concept("HTML") is True

def test_plausible_concept_rejects_ocr_fragments():
    # Word fragments that appeared in live E2E OCR runs
    for fragment in ("ano", "ity", "heh", "bene", "tae"):
        assert is_plausible_concept(fragment) is False, fragment

def test_plausible_concept_rejects_garbage():
    assert is_plausible_concept("hty") is False       # no vowel
    assert is_plausible_concept("aannup") is False    # doubled-run noise
    assert is_plausible_concept("qwrty") is False     # no vowel
    assert is_plausible_concept("ab") is False        # too short
    assert is_plausible_concept("") is False
    assert is_plausible_concept(None) is False

def test_plausible_concept_rejects_common_suffix_fragments():
    for fragment in ("tion", "ing", "ent", "ion", "ation"):
        assert is_plausible_concept(fragment) is False, fragment

def test_plausible_concept_rejects_long_glued_tokens():
    # Glued OCR chains of screen chrome — killed by the per-token length cap.
    assert is_plausible_concept("srketonviewgoorunferminalhelp") is False
    assert is_plausible_concept("problemsqutputoebugcontoleterminalport") is False
    assert is_plausible_concept("seuretagschpeudoxoomektsurepeudy") is False

def test_plausible_concept_rejects_consonant_cluster_noise():
    # dnkkhmackgrsswel has a 6-consonant run; 'strengths' is vowel-poor.
    assert is_plausible_concept("dnkkhmackgrsswel") is False
    assert is_plausible_concept("strengths") is False

def test_plausible_concept_rejects_observed_ocr_noise():
    # Sticky window-chrome misreads from live E2E tracking that pass the
    # generic structural rules — blocked by the explicit OCR-noise list.
    for noise in ("uktantigtaaty", "annletae", "dtrarre", "aofieedit",
                  "oreerat", "enoea", "aannup", "youlube", "exlorer"):
        assert is_plausible_concept(noise) is False, noise

def test_plausible_concept_rejects_stopword_concepts():
    assert is_plausible_concept("for") is False
    assert is_plausible_concept("the") is False
    assert is_plausible_concept("with") is False

def test_plausible_concept_keeps_vowel_heavy_technical_terms():
    # 'queue' is 80% vowels — the upper ratio bound must not kill real words.
    assert is_plausible_concept("queue") is True
    assert is_plausible_concept("binary tree") is True   # 'tree' is 50% doubled 'ee'
    assert is_plausible_concept("pytorch") is True       # 14% vowels
    assert is_plausible_concept("photosynthesis") is True  # 5-consonant 'synt h' run
