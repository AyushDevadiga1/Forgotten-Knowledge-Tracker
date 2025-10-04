# core/train_intent_classifier_large_edge.py
import numpy as np
import pandas as pd
import pickle
import random
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report

# -----------------------------
# 1. Generate Synthetic Multi-Modal Dataset
# -----------------------------
data = []

# Normal behavior
for _ in range(1000):
    # Idle
    data.append([
        random.randint(0, 2),          # OCR_count
        random.choice([0, 1]),          # audio_val
        random.randint(0, 60),          # attention_score
        random.randint(0, 2),           # interaction_rate
        "idle"
    ])
    # Passive
    data.append([
        random.randint(1, 5),
        1,
        random.randint(40, 70),
        random.randint(2, 10),
        "passive"
    ])
    # Studying
    data.append([
        random.randint(3, 50),
        2,
        random.randint(60, 100),
        random.randint(5, 50),
        "studying"
    ])

# -----------------------------
# 2. Add Edge Cases & Extreme Scenarios
# -----------------------------
for _ in range(100):
    # Extreme OCR spikes but low audio & interaction
    data.append([1000, 0, 10, 0, "idle"])
    # High interaction but silence & low OCR
    data.append([0, 0, 20, 100, "passive"])
    # Audio speech but OCR empty and attention low
    data.append([0, 2, 10, 1, "passive"])
    # All zeros
    data.append([0, 0, 0, 0, "idle"])
    # Max values in all features
    data.append([5000, 2, 100, 200, "studying"])
    # Random invalid OCR (negative)
    data.append([-5, 1, 50, 5, "passive"])
    # Random extreme attention spikes
    data.append([2, 1, 500, 5, "studying"])

# Convert to DataFrame
df = pd.DataFrame(data, columns=["OCR_count","audio_val","attention_score","interaction_rate","intent_label"])
df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # Shuffle
df.to_csv("core/intent_training_data_edge.csv", index=False)
print("Synthetic dataset with edge cases generated:", df.shape)

# -----------------------------
# 3. Prepare Features and Labels
# -----------------------------
X = df[["OCR_count","audio_val","attention_score","interaction_rate"]].values
y = df["intent_label"].values

le = LabelEncoder()
y_encoded = le.fit_transform(y)

# -----------------------------
# 4. Train/Test Split
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, stratify=y_encoded, random_state=42
)

# -----------------------------
# 5. Train XGBoost Classifier
# -----------------------------
clf = XGBClassifier(
    use_label_encoder=False,
    eval_metric='mlogloss',
    n_estimators=300,
    max_depth=6,
    random_state=42
)
clf.fit(X_train, y_train)

# -----------------------------
# 6. Evaluate
# -----------------------------
y_pred = clf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"Test Accuracy: {acc:.4f}\n")
print("Classification Report:\n", classification_report(y_test, y_pred, target_names=le.classes_))

# -----------------------------
# 7. Save Classifier and LabelEncoder
# -----------------------------
with open("core/intent_classifier.pkl", "wb") as f:
    pickle.dump(clf, f)
with open("core/intent_label_map.pkl", "wb") as f:
    pickle.dump(le, f)

print("Intent classifier and label map saved successfully.")
