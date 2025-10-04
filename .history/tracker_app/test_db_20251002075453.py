# core/preflight_check.py
from core.audio_module import record_audio, classify_audio
from core.intent_module import predict_intent
from core.session_manager import log_session
import numpy as np

def preflight_check():
    print("=== PRE-FLIGHT CHECK START ===")

    # 1️⃣ Check Audio Classifier
    try:
        audio_sample = record_audio(duration=1)  # 1 sec sample
        audio_label, audio_conf = classify_audio(audio_sample)
        print(f"Audio classification test passed: {audio_label} ({audio_conf:.2f})")
    except Exception as e:
        print(f"Audio classifier check FAILED: {e}")

    # 2️⃣ Check Intent Classifier
    try:
        test_features = {
            "ocr_keywords": ["test", "python"],
            "audio_label": audio_label,
            "attention_score": 50,
            "interaction_rate": 5
        }
        intent_result = predict_intent(**test_features, use_webcam=False)
        print(f"Intent prediction test passed: {intent_result['intent_label']} ({intent_result['confidence']:.2f})")
    except Exception as e:
        print(f"Intent classifier check FAILED: {e}")

    # 3️⃣ Check Session Logging
    try:
        log_session("Test Window", 1, audio_label, intent_result['intent_label'])
        print("Session logging test passed")
    except Exception as e:
        print(f"Session logging check FAILED: {e}")

    print("=== PRE-FLIGHT CHECK COMPLETED ===")

if __name__ == "__main__":
    preflight_check()
