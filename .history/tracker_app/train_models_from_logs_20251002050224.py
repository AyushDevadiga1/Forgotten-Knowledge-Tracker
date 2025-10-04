# scripts/test_models_on_logs.py

import sqlite3
import pickle
import numpy as np
from core.audio_module import extract_features as audio_extract_features
from core.intent_module import extract_features as intent_extract_features, predict_intent
from config import DB_PATH

# Load trained models
with open("core/audio_classifier.pkl", "rb") as f:
    audio_clf = pickle.load(f)

with open("core/intent_classifier.pkl", "rb") as f:
    intent_clf = pickle.load(f)

# If you saved label map for intent
try:
    with open("core/intent_label_map.pkl", "rb") as f:
        label_map = pickle.load(f)
        reverse_label_map = {v: k for k, v in label_map.items()}
except:
    label_map = reverse_label_map = None

# Load multi-modal logs
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT * FROM multi_modal_logs")
rows = cursor.fetchall()
columns = [col[0] for col in cursor.description]
conn.close()

print(f"Testing {len(rows)} rows from logs...\n")

for i, row in enumerate(rows[:10]):  # test first 10 rows for demo
    row_dict = dict(zip(columns, row))
    
    # --- Audio prediction ---
    # If actual audio is unavailable, we simulate features
    dummy_audio = np.random.rand(16000 * 5)
    features = audio_extract_features(dummy_audio).reshape(1, -1)
    audio_label = audio_clf.predict(features)[0]
    audio_conf = max(audio_clf.predict_proba(features)[0])
    
    # --- Intent prediction ---
    ocr_keywords = [] if row_dict["ocr_keywords"] is None else eval(row_dict["ocr_keywords"])
    attention_score = row_dict.get("attention_score", 0)
    interaction_rate = row_dict.get("interaction_rate", 0)
    
    intent_features = intent_extract_features(
        ocr_keywords,
        audio_label,
        attention_score,
        interaction_rate,
        use_webcam=False
    ).reshape(1, -1)
    
    intent_idx = intent_clf.predict(intent_features)[0]
    intent_conf = max(intent_clf.predict_proba(intent_features)[0])
    intent_label = reverse_label_map[intent_idx] if reverse_label_map else intent_idx
    
    print(f"Row {i+1}:")
    print(f"  Audio -> {audio_label} (confidence: {audio_conf:.2f})")
    print(f"  Intent -> {intent_label} (confidence: {intent_conf:.2f})\n")
