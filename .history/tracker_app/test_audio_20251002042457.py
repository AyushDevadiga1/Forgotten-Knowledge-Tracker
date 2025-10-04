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


//(venv) PS C:\Users\hp\Desktop\FKT\tracker_app> python test_audio.py
   id            timestamp                              window_title  ... interaction_rate intent_label  intent_confidence
0   1  2025-10-02 04:22:18  test_audio.py - FKT - Visual Studio Code  ...              0.0         idle                0.7
1   2  2025-10-02 04:22:20  test_audio.py - FKT - Visual Studio Code  ...              0.0         idle                0.7
2   3  2025-10-02 04:22:28  Multi-Modal Data Logging - Google Chrome  ...              2.0      passive                0.6
3   4  2025-10-02 04:22:30  test_audio.py - FKT - Visual Studio Code  ...             13.0      passive                0.6
4   5  2025-10-02 04:22:36                                       FKT  ...              3.0      passive                0.6

[5 rows x 9 columns]
//