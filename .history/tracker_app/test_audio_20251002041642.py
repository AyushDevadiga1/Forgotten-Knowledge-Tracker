# tests/test_model_evaluation.py

import os
import numpy as np
import pandas as pd
import pickle
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from core.audio_module import extract_features, classify_audio
from core.intent_module import predict_intent

# -----------------------------
# Paths
# -----------------------------
audio_model_path = "core/audio_classifier.pkl"
intent_model_path = "core/intent_classifier.pkl"
intent_label_map_path = "core/intent_label_map.pkl"

# -----------------------------
# 1️⃣ Load Audio Classifier
# -----------------------------
with open(audio_model_path, "rb") as f:
    audio_clf = pickle.load(f)

# -----------------------------
# 2️⃣ Load Intent Classifier & Label Map
# -----------------------------
with open(intent_model_path, "rb") as f:
    intent_clf = pickle.load(f)

with open(intent_label_map_path, "rb") as f:
    label_map = pickle.load(f)
reverse_label_map = {v: k for k, v in label_map.items()}

# -----------------------------
# 3️⃣ Generate Dummy Test Data
# -----------------------------
# Audio: 20 random samples (replace with real audio features if available)
X_audio_test = np.random.rand(20, 14)
y_audio_test = np.random.choice(["speech", "music", "silence"], size=20)

# Intent: 20 random samples
X_intent_test = np.random.randint(0, 10, size=(20, 4))
y_intent_test_labels = np.random.choice(list(label_map.keys()), size=20)
y_intent_test = np.array([label_map[label] for label in y_intent_test_labels])

# -----------------------------
# 4️⃣ Evaluate Audio Classifier
# -----------------------------
y_audio_pred = audio_clf.predict(X_audio_test)
audio_acc = accuracy_score(y_audio_test, y_audio_pred)
audio_report = classification_report(y_audio_test, y_audio_pred, output_dict=True)
audio_cm = confusion_matrix(y_audio_test, y_audio_pred)

print("=== Audio Classifier Metrics ===")
print("Accuracy:", audio_acc)
print(pd.DataFrame(audio_cm, index=["speech", "music", "silence"], columns=["speech", "music", "silence"]))
print("\nClassification Report:")
print(pd.DataFrame(audio_report).transpose())

# Save to CSV
os.makedirs("results", exist_ok=True)
pd.DataFrame(audio_report).transpose().to_csv("results/audio_metrics.csv", index=True)
pd.DataFrame(audio_cm, index=["speech", "music", "silence"], columns=["speech", "music", "silence"]).to_csv("results/audio_confusion_matrix.csv")

# -----------------------------
# 5️⃣ Evaluate Intent Classifier
# -----------------------------
y_intent_pred_int = intent_clf.predict(X_intent_test)
y_intent_pred = np.array([reverse_label_map[i] for i in y_intent_pred_int])
y_intent_true = y_intent_test_labels

intent_acc = accuracy_score(y_intent_true, y_intent_pred)
intent_report = classification_report(y_intent_true, y_intent_pred, output_dict=True)
intent_cm = confusion_matrix(y_intent_true, y_intent_pred, labels=list(label_map.keys()))

print("\n=== Intent Classifier Metrics ===")
print("Accuracy:", intent_acc)
print(pd.DataFrame(intent_cm, index=list(label_map.keys()), columns=list(label_map.keys())))
print("\nClassification Report:")
print(pd.DataFrame(intent_report).transpose())

# Save to CSV
pd.DataFrame(intent_report).transpose().to_csv("results/intent_metrics.csv", index=True)
pd.DataFrame(intent_cm, index=list(label_map.keys()), columns=list(label_map.keys())).to_csv("results/intent_confusion_matrix.csv")
