#test_model_audio.py

import sqlite3
import json
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import pickle
from config import DB_PATH
from core.intent_module import predict_intent  # assumes this function works with feature dict

# -----------------------------
# 1️⃣ Test Audio Classifier
# -----------------------------
def test_audio_classifier():
    # Load trained model
    with open("core/audio_classifier.pkl", "rb") as f:
        clf = pickle.load(f)
    
    # Example test data: X_test features and y_test labels
    # Replace with real features extracted from audio files
    X_test = np.random.rand(10, 14)  # 13 MFCC + 1 energy
    y_test = np.random.choice(["speech", "music", "silence"], size=10)

    y_pred = clf.predict(X_test)
    print("Audio Classifier Metrics")
    print("------------------------")
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Classification Report:\n", classification_report(y_test, y_pred))
    print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))
    print("\n")

# -----------------------------
# 2️⃣ Test Intent Classifier
# -----------------------------
def test_intent_classifier():
    # Fetch data from multi_modal_logs
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ocr_keywords, audio_label, attention_score, interaction_rate, intent_label FROM multi_modal_logs")
    rows = c.fetchall()
    conn.close()

    if not rows:
        print("No multi-modal logs found. Please log some sessions first.")
        return

    # Prepare features and labels
    X = []
    y = []
    for ocr_json, audio_label, attention, interaction, intent_label in rows:
        ocr_keywords = json.loads(ocr_json)
        feature = [
            len(ocr_keywords),          # OCR keyword count
            1 if audio_label == "speech" else 0,  # Simple encoding
            attention,
            interaction
        ]
        X.append(feature)
        y.append(intent_label)
    
    X = np.array(X)
    y = np.array(y)

    # Load trained intent model
    with open("core/intent_classifier.pkl", "rb") as f:
        intent_clf = pickle.load(f)
    
    # Evaluate
    y_pred = intent_clf.predict(X)
    print("Intent Classifier Metrics")
    print("-------------------------")
    print("Accuracy:", accuracy_score(y, y_pred))
    print("Classification Report:\n", classification_report(y, y_pred))
    print("Confusion Matrix:\n", confusion_matrix(y, y_pred))
    print("\n")

# -----------------------------
# 3️⃣ Run All Tests
# -----------------------------
if __name__ == "__main__":
    print("=== Testing Audio Classifier ===")
    test_audio_classifier()
    
    print("=== Testing Intent Classifier ===")
    test_intent_classifier()
