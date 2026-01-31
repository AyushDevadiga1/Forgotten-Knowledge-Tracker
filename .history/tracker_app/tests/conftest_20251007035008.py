#tests/conftest.py
import pytest
from core.db_manager import initialize_tables

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    initialize_tables()
