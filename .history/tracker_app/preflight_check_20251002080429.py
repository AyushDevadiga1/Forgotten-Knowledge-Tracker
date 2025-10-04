# cre/preflight_check.py
import sqlite3
import numpy as np
import pickle
import os
from config import DB_PATH

# -----------------------------
# Helper: Load pickle safely
# -----------------------------
def load_pickle(path, name):
    try:
        if os.path.exists(path):
            with open(path, "rb") as f:
                obj = pickle.load(f)
            print(f"{name} loaded.")
            return obj
        else:
            print(f"{name} not found.")
            return None
    except Exception as e:
        print(f"{name} loading failed: {e}")
        return None

# -----------------------------
# Load classifiers
# -----------------------------
audio_clf = load_pickle("core/audio_classifier.pkl", "Audio classifier")
intent_clf = load_pickle("core/intent_classifier.pkl", "Intent classifier")
intent_map = load_pickle("core/intent_label_map.pkl", "Intent label map")

# -----------------------------
# Database table & column checks
# -----------------------------
def test_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Sessions table
        c.execute("PRAGMA table_info(sessions)")
        columns = [col[1] for col in c.fetchall()]
        required = ["id", "start_ts", "end_ts", "app_name", "window_title", "interaction_rate"]
        missing = [col for col in required if col not in columns]
        if missing:
            print(f"Sessions table missing columns: {missing}")
        else:
            print("Sessions table OK")

        # Multi-modal logs table
        c.execute("PRAGMA table_info(multi_modal_logs)")
        columns = [col[1] for col in c.fetchall()]
        required = ["id","timestamp","window_title","ocr_keywords","audio_label",
                    "attention_score","interaction_rate","intent_label","intent_confidence"]
        missing = [col for col in required if col not in columns]
        if missing:
            print(f"Multi-modal logs table missing columns: {missing}")
        else:
            print("Multi-modal logs table OK")

        conn.close()
    except Exception as e:
        print(f"DB check failed: {e}")

# -----------------------------
# Feature extraction and intent tests
# -----------------------------
def test_features_and_intent():
    from core.intent_module import extract_features, predict_intent

    test_cases = [
        # Normal
        {"ocr_keywords": ["photosynthesis"], "audio_label": "speech", "attention_score": 80, "interaction_rate": 10},
        # Empty OCR
        {"ocr_keywords": [], "audio_label": "silence", "attention_score": 50, "interaction_rate": 0},
        # Invalid OCR type
        {"ocr_keywords": 12345, "audio_label": "music", "attention_score": 60, "interaction_rate": 3},
        # Unknown audio label
        {"ocr_keywords": ["code"], "audio_label": "noise", "attention_score": 70, "interaction_rate": 5},
        # Extreme values
        {"ocr_keywords": ["x"]*1000, "audio_label": "speech", "attention_score": 200, "interaction_rate": 1000},
    ]

    for i, tc in enumerate(test_cases, 1):
        try:
            feats = extract_features(**tc)
            print(f"Feature extraction test {i}: {feats}")

            intent = predict_intent(**tc)
            print(f"Intent prediction test {i}: {intent['intent_label']}, Confidence: {intent['confidence']}")
        except Exception as e:
            print(f"Test {i} failed: {e}")

# -----------------------------
# Run everything
# -----------------------------
if __name__ == "__main__":
    print("=== STRICT PRE-FLIGHT TRACKER TEST START ===")
    test_db()
    test_features_and_intent()
    print("=== STRICT PRE-FLIGHT TRACKER TEST COMPLETED ===")
