# test_tracker.py
import sqlite3
import numpy as np
import pickle
import os
from config import DB_PATH

# -----------------------------
# Load classifiers
# -----------------------------
audio_clf_path = "core/audio_classifier.pkl"
intent_clf_path = "core/intent_classifier.pkl"
intent_map_path = "core/intent_label_map.pkl"

def load_pickle(path, name):
    if os.path.exists(path):
        with open(path, "rb") as f:
            obj = pickle.load(f)
        print(f"{name} loaded.")
        return obj
    else:
        print(f"{name} not found.")
        return None

audio_clf = load_pickle(audio_clf_path, "Audio classifier")
intent_clf = load_pickle(intent_clf_path, "Intent classifier")
intent_map = load_pickle(intent_map_path, "Intent label map")

# -----------------------------
# Database tests
# -----------------------------
def test_db_tables():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Check sessions table
        c.execute("PRAGMA table_info(sessions)")
        columns = [col[1] for col in c.fetchall()]
        required_cols = ["id", "start_ts", "end_ts", "app_name", "window_title", "interaction_rate"]
        missing = [col for col in required_cols if col not in columns]
        if missing:
            print(f"Sessions table missing columns: {missing}")
        else:
            print("Sessions table OK.")

        # Check multi_modal_logs table
        c.execute("PRAGMA table_info(multi_modal_logs)")
        columns = [col[1] for col in c.fetchall()]
        required_cols = ["id", "timestamp", "window_title", "ocr_keywords", "audio_label", 
                         "attention_score", "interaction_rate", "intent_label", "intent_confidence"]
        missing = [col for col in required_cols if col not in columns]
        if missing:
            print(f"Multi-modal logs table missing columns: {missing}")
        else:
            print("Multi-modal logs table OK.")

        conn.close()
    except Exception as e:
        print(f"Database test failed: {e}")

# -----------------------------
# Feature extraction tests
# -----------------------------
def test_feature_extraction():
    from core.intent_module import extract_features, predict_intent

    # Test valid input
    feats = extract_features(["keyword1", "keyword2"], "speech", 80, 10)
    print("Feature extraction valid input:", feats)

    # Test empty OCR
    feats = extract_features([], "silence", 50, 0)
    print("Feature extraction empty OCR:", feats)

    # Test invalid OCR type
    feats = extract_features(123, "music", 60, 5)
    print("Feature extraction invalid OCR:", feats)

# -----------------------------
# Intent prediction tests
# -----------------------------
def test_intent_prediction():
    from core.intent_module import predict_intent

    test_cases = [
        {"ocr_keywords": ["study"], "audio_label": "speech", "attention_score": 80, "interaction_rate": 10},
        {"ocr_keywords": [], "audio_label": "silence", "attention_score": 50, "interaction_rate": 0},
        {"ocr_keywords": ["code"], "audio_label": "music", "attention_score": 50, "interaction_rate": 3},
    ]
    for i, tc in enumerate(test_cases, 1):
        result = predict_intent(**tc)
        print(f"Test case {i}: Input: {tc} -> Predicted intent: {result['intent_label']}, Confidence: {result['confidence']}")

# -----------------------------
# Run all tests
# -----------------------------
if __name__ == "__main__":
    print("=== PRE-FLIGHT TRACKER TEST START ===")
    test_db_tables()
    test_feature_extraction()
    test_intent_prediction()
    print("=== PRE-FLIGHT TRACKER TEST COMPLETED ===")
