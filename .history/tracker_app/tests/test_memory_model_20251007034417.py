#tests/test_memory_model.py
from core.memory_model import forgetting_curve, log_decay_to_db

def test_forgetting_curve_shape():
    scores = [forgetting_curve(t) for t in range(5)]
    assert all(0 <= s <= 1 for s in scores)
    assert scores[0] > scores[-1]  # should decay over time

def test_log_decay_to_db():
    result = log_decay_to_db("test_keyword", 0.8, "unit_test")
    assert result is True
