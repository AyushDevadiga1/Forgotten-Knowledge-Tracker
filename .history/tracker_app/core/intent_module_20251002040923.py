# tests/test_audio.py

import os
import numpy as np
import pickle
from core.audio_module import extract_features, classify_audio, audio_pipeline
from core.intent_module import predict_intent

# -----------------------------
# 1️⃣ Ensure Audio Classifier Exists
# -----------------------------
audio_model_path = "core/audio_classifier.pkl"
if not os.path.exists(audio_model_path):
    print("Training dummy audio classifier...")
    from sklearn.ensemble import RandomForestClassifier
    
    # Generate dummy features: 50 samples, 13 MFCC + 1 energy
    X = np.random.rand(50, 14)
    y = np.random.choice(["speech", "music", "silence"], size=50)
    
    clf = RandomForestClassifier(n_estimators=50)
    clf.fit(X, y)
    
    os.makedirs("core", exist_ok=True)
    with open(audio_model_path, "wb") as f:
        pickle.dump(clf, f)
    print("Audio classifier trained and saved.")

# -----------------------------
# 2️⃣ Ensure Intent Classifier Exists
# -----------------------------
intent_model_path = "core/intent_classifier.pkl"
if not os.path.exists(intent_model_path):
    print("Training dummy intent classifier...")
    from xgboost import XGBClassifier
    
    # Features: OCR_count, audio_val, attention_score, interaction_rate
    X = np.random.randint(0, 10, size=(50, 4))
    y = np.random.choice(["studying", "idle", "passive"], size=50)
    
    intent_clf = XGBClassifier(use_label_encoder=False, eval_metric='mlogloss')
    intent_clf.fit(X, y)
    
    with open(intent_model_path, "wb") as f:
        pickle.dump(intent_clf, f)
    print("Intent classifier trained and saved.")

# -----------------------------
# 3️⃣ Test Audio Module
# -----------------------------
print("\n=== Testing Audio Module ===")
audio_result = audio_pipeline()
print("Audio label:", audio_result['audio_label'], "| Confidence:", audio_result['confidence'])

# -----------------------------
# 4️⃣ Test Intent Module
# -----------------------------
print("\n=== Testing Intent Module ===")
intent_result = predict_intent(
    ocr_keywords=["photosynthesis", "chlorophyll"],
    audio_label=audio_result['audio_label'],
    attention_score=80,
    interaction_rate=10
)
print("Intent prediction:", intent_result)
