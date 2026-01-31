# test_fixes.py
from core.audio_module import extract_features, record_audio
import numpy as np

# Test audio feature dimensions
print("Testing audio feature dimensions...")
test_audio = record_audio(duration=1)  # 1 second for quick test
features = extract_features(test_audio)
print(f"Audio features shape: {features.shape}, expected: (14,)")

# Test intent classifier
from core.intent_module import predict_intent
print("\nTesting intent classification...")
result = predict_intent(
    ocr_keywords={"python": 0.8, "programming": 0.7},
    audio_label="speech", 
    attention_score=75,
    interaction_rate=8
)
print(f"Intent result: {result}")

# Test webcam
from core.webcam_module import webcam_pipeline
print("\nTesting webcam...")
webcam_result = webcam_pipeline(num_frames=3)  # Fewer frames for quick test
print(f"Webcam result: {webcam_result}")

print("\nAll tests completed!")