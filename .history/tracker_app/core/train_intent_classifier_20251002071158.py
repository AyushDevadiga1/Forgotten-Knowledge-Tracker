# core/train_intent_classifier.py
import numpy as np
import pickle
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# -----------------------------
# Example: Load or generate dataset
# Replace this with your real multi-modal feature extraction
# -----------------------------
# Features: [num_ocr_keywords, audio_label_int, attention_score, interaction_rate]
# Labels: 'idle', 'passive', 'studying'

# Example synthetic dataset (replace with your full dataset)
X = np.array([
    [0, 0, 50, 0],
    [5, 2, 80, 10],
    [3, 1, 30, 5],
    [1, 0, 60, 2],
    [2, 2, 70, 8],
    [4, 1, 55, 6],
    [0, 0, 50, 1],
    [6, 2, 90, 12],
    [3, 1, 40, 4],
    [2, 0, 60, 3]
])
y = np.array([
    'idle', 'studying', 'passive', 'idle', 'studying',
    'passive', 'idle', 'studying', 'passive', 'idle'
])

# -----------------------------
# Encode string labels to integers
# -----------------------------
intent_labels = sorted(list(set(y)))  # ['idle', 'passive', 'studying']
label_to_int = {lbl: i for i, lbl in enumerate(intent_labels)}
y_int = np.array([label_to_int[label] for label in y])

# -----------------------------
# Train-test split
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y_int, test_size=0.2, random_state=42, stratify=y_int
)

# -----------------------------
# Train XGBoost classifier
# -----------------------------
clf = XGBClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    use_label_encoder=False,
    eval_metric="mlogloss"
)
clf.fit(X_train, y_train)

# -----------------------------
# Evaluate model
# -----------------------------
y_pred = clf.predict(X_test)
int_to_label = {i: lbl for lbl, i in label_to_int.items()}
y_test_labels = [int_to_label[i] for i in y_test]
y_pred_labels = [int_to_label[i] for i in y_pred]

print("Accuracy:", accuracy_score(y_test_labels, y_pred_labels))
print(classification_report(y_test_labels, y_pred_labels))

# -----------------------------
# Save classifier and label map
# -----------------------------
with open("core/intent_classifier.pkl", "wb") as f:
    pickle.dump(clf, f)
with open("core/intent_label_map.pkl", "wb") as f:
    pickle.dump(int_to_label, f)

print("Intent classifier and label map saved successfully.")
