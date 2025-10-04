# test_audio.py

import os
import numpy as np
import pickle
from core.audio_module import extract_features, classify_audio, audio_pipeline
from core.intent_module import predict_intent

# -----------------------------
# Paths
# -----------------------------
audio_model_path = "core/audio_classifier.pkl"
intent_model_path = "core/intent_classifier.pkl"
intent_label_map_path = "core/intent_label_map.pkl"

# -----------------------------
# 1️⃣ Ensure Audio Classifier Exists
# -----------------------------
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
if not os.path.exists(intent_model_path) or not os.path.exists(intent_label_map_path):
    print("Training dummy intent classifier...")
    from xgboost import XGBClassifier

    # Features: OCR_count, audio_val, attention_score, interaction_rate
    X = np.random.randint(0, 10, size=(50, 4))
    y = np.random.choice(["studying", "idle", "passive"], size=50)

    # Map string labels to integers
    label_map = {label: idx for idx, label in enumerate(sorted(set(y)))}
    y_int = np.array([label_map[label] for label in y])

    intent_clf = XGBClassifier(use_label_encoder=False, eval_metric='mlogloss')
    intent_clf.fit(X, y_int)

    os.makedirs("core", exist_ok=True)
    with open(intent_model_path, "wb") as f:
        pickle.dump(intent_clf, f)
    with open(intent_label_map_path, "wb") as f:
        pickle.dump(label_map, f)

    print("Intent classifier trained and saved.")

# -----------------------------
# 3️⃣ Load label map for predictions
# -----------------------------
with open(intent_label_map_path, "rb") as f:
    label_map = pickle.load(f)
reverse_label_map = {v: k for k, v in label_map.items()}

# -----------------------------
# 4️⃣ Test Audio Module
# -----------------------------
print("\n=== Testing Audio Module ===")
audio_result = audio_pipeline()
print("Audio label:", audio_result['audio_label'], "| Confidence:", audio_result['confidence'])

# -----------------------------
# 5️⃣ Test Intent Module
# -----------------------------
print("\n=== Testing Intent Module ===")
# Example multi-modal data
intent_features = {
    "ocr_keywords": ["photosynthesis", "chlorophyll"],
    "audio_label": audio_result['audio_label'],
    "attention_score": 80,
    "interaction_rate": 10,
    "use_webcam": False
}

# Predict using your pipeline
raw_result = predict_intent(**intent_features)

# If model is numeric, map back to string
if "confidence" in raw_result and raw_result["intent_label"].isdigit():
    label_int = int(raw_result["intent_label"])
    raw_result["intent_label"] = reverse_label_map.get(label_int, raw_result["intent_label"])

print("Intent prediction:", raw_result)
