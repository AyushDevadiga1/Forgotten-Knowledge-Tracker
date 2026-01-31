# tests/test_intent.py
import pytest
from core.intent_module import predict_intent
from core.db_module import init_multi_modal_db, DB_PATH
import sqlite3

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Ensure multi_modal_logs table exists before intent tests"""
    init_multi_modal_db()

def test_predict_intent_returns_dict():
    result = predict_intent(
        ocr_keywords=["machine", "learning"],
        audio_label="speech",
        attention_score=80,
        interaction_rate=10
    )
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "intent_label" in result
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0, "Confidence should be between 0 and 1"

def test_fallback_intent_logic():
    result = predict_intent(
        ocr_keywords=[],
        audio_label="speech",
        attention_score=40,
        interaction_rate=6
    )
    # Since audio_label=speech, interaction_rate>5, attention_score<50 => passive fallback
    assert result["intent_label"] in ["passive", "studying", "idle"], "Intent should be valid fallback"
    assert 0.0 <= result["confidence"] <= 1.0

def test_logging_inserts_row():
    ocr_test = ["test"]
    audio_test = "speech"
    att_test = 70
    interact_test = 8

    predict_intent(
        ocr_keywords=ocr_test,
        audio_label=audio_test,
        attention_score=att_test,
        interaction_rate=interact_test
    )

    # Verify the row was inserted in multi_modal_logs
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM multi_modal_logs WHERE ocr_keywords=? ORDER BY id DESC LIMIT 1", (str(ocr_test),))
    row = cursor.fetchone()
    conn.close()

    assert row is not None, "A row should be logged in multi_modal_logs"
    assert row[3] == str(ocr_test), "OCR keywords should match logged value"
    assert row[4] == audio_test, "Audio label should match logged value"
    assert row[5] == att_test, "Attention score should match logged value"
