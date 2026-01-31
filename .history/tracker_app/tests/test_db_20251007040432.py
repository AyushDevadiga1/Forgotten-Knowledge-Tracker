# tests/test_db.py
import sqlite3
import pytest
from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db, log_multi_modal_event
from config import DB_PATH
from datetime import datetime

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Initialize all tables before tests"""
    init_db()
    init_multi_modal_db()
    init_memory_decay_db()

def test_sessions_table_exists():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    conn.close()
    assert "sessions" in tables, "Sessions table should exist"

def test_multi_modal_logs_table_exists():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    conn.close()
    assert "multi_modal_logs" in tables, "Multi-modal logs table should exist"

def test_memory_decay_table_exists():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    conn.close()
    assert "memory_decay" in tables, "Memory decay table should exist"

def test_log_multi_modal_event_inserts_row():
    log_multi_modal_event(
        window_title="Test Window",
        ocr_keywords="test",
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.5,
        intent_label="study",
        intent_confidence=0.9,
        memory_score=0.8,
        source_module="pytest"
    )

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM multi_modal_logs ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    assert row is not None, "Inserted row should exist in multi_modal_logs"
    assert row[2] == "Test Window", "Window title should match"
    assert row[3] == "test", "OCR keywords should match"
    assert row[4] == "silence", "Audio label should match"
    assert row[5] == 50.0, "Attention score should match"
    assert row[8] == 0.8, "Memory score should match"
    assert row[9] == "pytest", "Source module should match"
