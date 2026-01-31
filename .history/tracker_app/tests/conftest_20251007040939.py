# tests/conftest.py
import os
import sys
import pytest

# Dynamically add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Initialize all required database tables for tests"""
    init_db()
    init_multi_modal_db()
    init_memory_decay_db()
