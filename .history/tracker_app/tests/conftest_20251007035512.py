# tests/conftest.py
import os
import sys
import pytest

# Dynamically add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db_manager import initialize_tables  # ✅ correct import

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    initialize_tables()
