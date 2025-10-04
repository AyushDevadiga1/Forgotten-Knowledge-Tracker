# core/train_intent_classifier_large.py
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

for _ in range(1000):  # 1000 samples per class
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

# Convert to DataFrame
df = pd.DataFrame(data, columns=["OCR_count", "audio_val", "attention_score", "interaction_rate", "intent_label"])
df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # Shuffle
df.to_csv("core/intent_training_data_large.csv", index=False)
print("Synthetic dataset generated:", df.shape)

# -----------------------------
# 2. Prepare Features and Labels
# -----------------------------
X = df[["OCR_count","audio_val","attention_score","interaction_rate"]].values
y = df["intent_label"].values

le = LabelEncoder()
y_encoded = le.fit_transform(y)

# -----------------------------
# 3. Train/Test Split
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, stratify=y_encoded, random_state=42
)

# -----------------------------
# 4. Train XGBoost Classifier
# -----------------------------
clf = XGBClassifier(
    use_label_encoder=False,
    eval_metric='mlogloss',
    n_estimators=200,
    max_depth=5,
    random_state=42
)
clf.fit(X_train, y_train)

# -----------------------------
# 5. Evaluate
# -----------------------------
y_pred = clf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"Test Accuracy: {acc:.4f}\n")
print("Classification Report:\n", classification_report(y_test, y_pred, target_names=le.classes_))

# -----------------------------
# 6. Save Classifier and LabelEncoder
# -----------------------------
with open("core/intent_classifier.pkl", "wb") as f:
    pickle.dump(clf, f)
with open("core/intent_label_map.pkl", "wb") as f:
    pickle.dump(le, f)

print("Intent classifier and label map saved successfully.")
