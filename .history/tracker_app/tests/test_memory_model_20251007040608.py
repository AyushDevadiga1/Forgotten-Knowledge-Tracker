# tests/test_memory_model.py
import pytest
from datetime import datetime, timedelta
from core.memory_model import compute_memory_score, schedule_next_review, forgetting_curve, log_forgetting_curve
from core.db_module import init_multi_modal_db, DB_PATH
import sqlite3

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Ensure multi_modal_logs table exists before logging tests"""
    init_multi_modal_db()

def test_compute_memory_score_bounds():
    last_review = datetime.now() - timedelta(hours=5)
    score = compute_memory_score(last_review, lambda_val=0.1, intent_conf=0.9, attention_score=80, audio_conf=1.0)
    assert 0.0 <= score <= 1.0, "Memory score must be between 0 and 1"

def test_forgetting_curve_values():
    values = [forgetting_curve(t) for t in range(5)]
    assert all(0.0 <= v <= 1.0 for v in values), "All forgetting curve values must be between 0 and 1"
    assert values[0] > values[-1], "Values should decay over time"

def test_schedule_next_review_low_memory():
    last_review = datetime.now() - timedelta(hours=5)
    next_review = schedule_next_review(last_review, memory_score=0.5, lambda_val=0.1, hours_min=1)
    assert next_review > datetime.now(), "Next review should be in the future when memory score is low"

def test_schedule_next_review_high_memory():
    last_review = datetime.now() - timedelta(hours=5)
    next_review = schedule_next_review(last_review, memory_score=0.9, lambda_val=0.1)
    assert next_review > last_review, "Next review should be after last review"

def test_log_forgetting_curve_inserts_row():
    last_seen = datetime.now() - timedelta(hours=5)
    predicted = log_forgetting_curve("TestConcept", last_seen, observed_usage=2, memory_strength=1.25)

    assert 0.0 <= predicted <= 1.0, "Predicted recall must be between 0 and 1"

    # Verify that the log was inserted into multi_modal_logs
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM multi_modal_logs WHERE ocr_keywords='TestConcept' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    assert row is not None, "A row should be inserted into multi_modal_logs for the forgetting curve"
    assert row[3] == "TestConcept", "OCR keywords should match the concept logged"
    assert row[7] == "memory_decay", "Intent label should be 'memory_decay'"
