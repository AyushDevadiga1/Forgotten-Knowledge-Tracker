# core/train_intent_classifier.py
import numpy as np
import pickle
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# -----------------------------
# Intent labels
# -----------------------------
intent_labels = ["studying", "passive", "idle"]
label_map = {i: lbl for i, lbl in enumerate(intent_labels)}

# -----------------------------
# Generate synthetic training data
# -----------------------------
# Features: [ocr_count, audio_val, attention_score, interaction_rate]
# audio_val: 0=silence, 1=music, 2=speech
np.random.seed(42)
num_samples = 5000

X = []
y = []

for _ in range(num_samples):
    ocr_count = np.random.randint(0, 15)          # 0 to 15 keywords
    audio_val = np.random.choice([0, 1, 2])       # silence/music/speech
    attention_score = np.random.randint(0, 101)   # 0-100 faces/attention
    interaction_rate = np.random.randint(0, 20)   # keyboard+mouse events

    # Rule-based labeling for synthetic data
    if audio_val == 2 and interaction_rate > 5:
        if attention_score > 50:
            label = "studying"
        else:
            label = "passive"
    elif interaction_rate < 2:
        label = "idle"
    else:
        label = "passive"

    X.append([ocr_count, audio_val, attention_score, interaction_rate])
    y.append(label)

X = np.array(X)
y = np.array(y)

# -----------------------------
# Train-test split
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# -----------------------------
# Train classifier
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
# Evaluate
# -----------------------------
y_pred = clf.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred))

# -----------------------------
# Save classifier and label map
# -----------------------------
with open("core/intent_classifier.pkl", "wb") as f:
    pickle.dump(clf, f)
with open("core/intent_label_map.pkl", "wb") as f:
    pickle.dump(label_map, f)

print("Intent classifier and label map saved successfully.")
