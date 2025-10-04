# tests/test_modules_simple.py

from core.audio_module import audio_pipeline
from core.intent_module import predict_intent

# -----------------------------
# 1️⃣ Test Audio Module
# -----------------------------
print("=== Testing Audio Module ===")
audio_result = audio_pipeline()
print("Audio label:", audio_result['audio_label'])
print("Confidence:", audio_result['confidence'])

# -----------------------------
# 2️⃣ Test Intent Module
# -----------------------------
print("\n=== Testing Intent Module ===")
# Example multi-modal input
sample_data = {
    "ocr_keywords": ["photosynthesis", "chlorophyll"],
    "audio_label": audio_result['audio_label'],
    "attention_score": 80,       # number of faces detected
    "interaction_rate": 10,      # keyboard+mouse events
    "use_webcam": False           # webcam off for test
}

intent_result = predict_intent(**sample_data)
print("Predicted Intent:", intent_result['intent_label'])
print("Confidence:", intent_result['confidence'])


