# tests/evaluate_models_real.py

import os
import sqlite3
import numpy as np
import pandas as pd
import pickle
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from core.audio_module import extract_features
from core.intent_module import extract_features as intent_extract_features

# -----------------------------
# Paths
# -----------------------------
DB_PATH = "tracker_app.db"  # adjust if your DB path is different
audio_model_path = "core/audio_classifier.pkl"
intent_model_path = "core/intent_classifier.pkl"
intent_label_map_path = "core/intent_label_map.pkl"

# -----------------------------
# 1️⃣ Load models
# -----------------------------
with open(audio_model_path, "rb") as f:
    audio_clf = pickle.load(f)

with open(intent_model_path, "rb") as f:
    intent_clf = pickle.load(f)

with open(intent_label_map_path, "rb") as f:
    label_map = pickle.load(f)
reverse_label_map = {v: k for k, v in label_map.items()}

# -----------------------------
# 2️⃣ Load multi-modal logs
# -----------------------------
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM multi_modal_logs", conn)
conn.close()

if df.empty:
    raise ValueError("No multi-modal logs found. Run tracker to collect data first.")

# -----------------------------
# 3️⃣ Prepare Audio Features
# -----------------------------
X_audio = []
y_audio = []

for _, row in df.iterrows():
    # Convert stored audio_label to numeric for classifier features
    audio_label = row["audio_label"]
    y_audio.append(audio_label)

    # Normally we'd extract MFCC from audio clips; here we assume features are stored as dummy MFCC
    # Replace this part if you have actual audio recordings
    dummy_audio = np.random.rand(16000 * 5)  # 5 sec synthetic audio
    features = extract_features(dummy_audio)
    X_audio.append(features)

X_audio = np.array(X_audio)

# -----------------------------
# 4️⃣ Prepare Intent Features
# -----------------------------
X_intent = []
y_intent = []

for _, row in df.iterrows():
    ocr_keywords = [] if row["ocr_keywords"] is None else eval(row["ocr_keywords"])
    audio_label = row["audio_label"]
    attention_score = row["attention_score"] or 0
    interaction_rate = row["interaction_rate"] or 0
    intent_label = row["intent_label"]

    X_feat = intent_extract_features(
        ocr_keywords,
        audio_label,
        attention_score,
        interaction_rate,
        use_webcam=True
    )
    X_intent.append(X_feat.flatten())
    y_intent.append(label_map.get(intent_label, 0))  # convert to numeric

X_intent = np.array(X_intent)
y_intent = np.array(y_intent)

# -----------------------------
# 5️⃣ Evaluate Audio Classifier
# -----------------------------
y_audio_pred = audio_clf.predict(X_audio)
audio_acc = accuracy_score(y_audio, y_audio_pred)
audio_report = classification_report(y_audio, y_audio_pred, output_dict=True)
audio_cm = confusion_matrix(y_audio, y_audio_pred, labels=["speech", "music", "silence"])

print("=== Audio Classifier Metrics ===")
print("Accuracy:", audio_acc)
print(pd.DataFrame(audio_cm, index=["speech", "music", "silence"], columns=["speech", "music", "silence"]))
print(pd.DataFrame(audio_report).transpose())

os.makedirs("results", exist_ok=True)
pd.DataFrame(audio_report).transpose().to_csv("results/audio_metrics_real.csv", index=True)
pd.DataFrame(audio_cm, index=["speech", "music", "silence"], columns=["speech", "music", "silence"]).to_csv("results/audio_confusion_matrix_real.csv")

# -----------------------------
# 6️⃣ Evaluate Intent Classifier
# -----------------------------
y_intent_pred_int = intent_clf.predict(X_intent)
y_intent_pred = np.array([reverse_label_map[i] for i in y_intent_pred_int])
y_intent_true = np.array([reverse_label_map[i] for i in y_intent])

intent_acc = accuracy_score(y_intent_true, y_intent_pred)
intent_report = classification_report(y_intent_true, y_intent_pred, output_dict=True)
intent_cm = confusion_matrix(y_intent_true, y_intent_pred, labels=list(label_map.keys()))

print("\n=== Intent Classifier Metrics ===")
print("Accuracy:", intent_acc)
print(pd.DataFrame(intent_cm, index=list(label_map.keys()), columns=list(label_map.keys())))
print(pd.DataFrame(intent_report).transpose())

pd.DataFrame(intent_report).transpose().to_csv("results/intent_metrics_real.csv", index=True)
pd.DataFrame(intent_cm, index=list(label_map.keys()), columns=list(label_map.keys())).to_csv("results/intent_confusion_matrix_real.csv")
