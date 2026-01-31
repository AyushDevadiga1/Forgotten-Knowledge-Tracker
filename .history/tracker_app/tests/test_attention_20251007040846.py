# tests/test_attention.py
import pytest
import numpy as np
from core.webcam_module import eye_aspect_ratio, compute_attention_score

def test_eye_aspect_ratio_correctness():
    # Simulate a simple eye shape with known distances
    eye = np.array([
        [0, 0],
        [1, 2],
        [2, 2],
        [3, 0],
        [2, -2],
        [1, -2]
    ])
    ear = eye_aspect_ratio(eye)
    assert isinstance(ear, float), "EAR should return a float"
    assert ear > 0, "EAR should be positive"

def test_compute_attention_score_bounds():
    ear_values = [0.25, 0.23, 0.26, 0.24]
    score = compute_attention_score(ear_values)
    assert 0 <= score <= 100, "Attention score should be between 0 and 100"

def test_attention_score_zero_when_no_face():
    # Simulate no face detected scenario
    attention_score = compute_attention_score([])
    assert attention_score == 0, "Attention score should be 0 when no EAR values"
