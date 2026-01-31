#
from core import audio

def test_audio_classifier_load():
    model = AudioClassifier()
    label, confidence = model.predict_audio("core/sample_silence.wav")
    assert label in ["speech", "silence", "music"]
    assert 0 <= confidence <= 1
