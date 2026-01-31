# tests/test_audio.py
import pytest
import numpy as np
from core.audio_module import extract_features, classify_audio, record_audio
from core.db_module import init_multi_modal_db, DB_PATH
import sqlite3

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Ensure multi_modal_logs table exists before audio tests"""
    init_multi_modal_db()

def test_extract_features_shape():
    mock_audio = np.zeros(16000 * 5)  # 5 seconds of silence
    features = extract_features(mock_audio)
    assert features.shape[0] == 14, "Feature vector should have length 14"

def test_classify_audio_returns_tuple():
    mock_audio = np.zeros(16000 * 5)  # silence
    label, confidence = classify_audio(mock_audio)
    assert isinstance(label, str)
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0, "Confidence should be between 0 and 1"

def test_classify_audio_logging():
    mock_audio = np.zeros(16000 * 5)
    label, confidence = classify_audio(mock_audio)

    # Verify DB logging
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM multi_modal_logs WHERE audio_label=? ORDER BY id DESC LIMIT 1", (label,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None, "Audio classification should be logged in multi_modal_logs"
    assert row[4] == label, "Logged audio label should match classification output"

def test_record_audio_returns_array():
    audio = record_audio()
    assert isinstance(audio, np.ndarray), "Recorded audio should be a numpy array"
    assert audio.shape[0] == 16000 * 5, "Default recorded audio should be 5 seconds"
