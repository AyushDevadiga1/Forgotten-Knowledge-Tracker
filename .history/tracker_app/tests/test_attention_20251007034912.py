from core.webcam_module import compute_attention_score

def test_attention_score_validity():
    ear_values = [0.25, 0.23, 0.26, 0.24]
    score = compute_attention_score(ear_values)
    assert 0 <= score <= 100
