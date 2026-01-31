#tests/test_intent.py
from core.intent_m import IntentClassifier

def test_intent_prediction():
    clf = IntentClassifier()
    text = "I am studying machine learning"
    label, confidence = clf.predict_intent(text)
    assert isinstance(label, str)
    assert 0 <= confidence <= 1
