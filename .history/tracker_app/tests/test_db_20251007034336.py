#
import sqlite3
from config import DB_PATH
from core.db_module import initialize_tables

def test_database_integrity():
    initialize_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    conn.close()
    assert "sessions" in tables
    assert "multi_modal_logs" in tables
    assert "memory_decay" in tables
