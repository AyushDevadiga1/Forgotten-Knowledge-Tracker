# core/train_intent_classifier.py
import numpy as np
import pickle
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score

# -----------------------------
# Example multi-modal dataset
# -----------------------------
# Each row: [OCR_count, audio_val, attention_score, interaction_rate]
X = np.array([
    [0, 0, 50, 0],      # idle
    [1, 0, 40, 1],      # idle
    [5, 2, 80, 10],     # studying
    [4, 2, 75, 9],      # studying
    [3, 1, 30, 5],      # passive
    [2, 1, 20, 3],      # passive
    [6, 2, 90, 12],     # studying
    [0, 0, 55, 0],      # idle
    [2, 1, 25, 4],      # passive
])

y = np.array([
    'idle',
    'idle',
    'studying',
    'studying',
    'passive',
    'passive',
    'studying',
    'idle',
    'passive'
])

# -----------------------------
# Encode string labels to numbers
# -----------------------------
le = LabelEncoder()
y_encoded = le.fit_transform(y)  # 0,1,2

print("Classes:", le.classes_)

# -----------------------------
# Train/test split
# -----------------------------
# Ensure test size >= number of classes
test_size = max(0.2, len(np.unique(y_encoded)) / len(y_encoded))
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=test_size, random_state=42, stratify=y_encoded
)

# -----------------------------
# Train XGBoost classifier
# -----------------------------
clf = XGBClassifier(
    use_label_encoder=False,
    eval_metric='mlogloss',
    n_estimators=100,
    max_depth=3,
    random_state=42
)

clf.fit(X_train, y_train)

# -----------------------------
# Evaluate
# -----------------------------
y_pred = clf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"Test Accuracy: {acc:.2f}")

# Show decoded predictions
decoded_preds = le.inverse_transform(y_pred)
print("Predictions:", decoded_preds)

# -----------------------------
# Save classifier and LabelEncoder
# -----------------------------
with open("core/intent_classifier.pkl", "wb") as f:
    pickle.dump(clf, f)
with open("core/intent_label_map.pkl", "wb") as f:
    pickle.dump(le, f)

print("Intent classifier and label map saved.")
