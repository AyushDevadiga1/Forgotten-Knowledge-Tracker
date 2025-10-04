import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sklearn.metrics import classification_report

# -----------------------------
# Generate synthetic dataset
# -----------------------------
np.random.seed(42)

NUM_SAMPLES_PER_CLASS = 50  # increase for more robustness

# Features: [ocr_val, audio_val, attention_val, interaction_rate]
idle_features = np.column_stack([
    np.random.randint(0, 2, NUM_SAMPLES_PER_CLASS),       # ocr_val
    np.zeros(NUM_SAMPLES_PER_CLASS, dtype=int),           # audio_val
    np.random.randint(40, 60, NUM_SAMPLES_PER_CLASS),     # attention_val
    np.random.randint(0, 2, NUM_SAMPLES_PER_CLASS)        # interaction_rate
])

passive_features = np.column_stack([
    np.random.randint(1, 5, NUM_SAMPLES_PER_CLASS),       # ocr_val
    np.ones(NUM_SAMPLES_PER_CLASS, dtype=int),            # audio_val (music)
    np.random.randint(20, 50, NUM_SAMPLES_PER_CLASS),     # attention_val
    np.random.randint(3, 7, NUM_SAMPLES_PER_CLASS)        # interaction_rate
])

studying_features = np.column_stack([
    np.random.randint(3, 10, NUM_SAMPLES_PER_CLASS),      # ocr_val
    np.full(NUM_SAMPLES_PER_CLASS, 2),                    # audio_val (speech)
    np.random.randint(60, 100, NUM_SAMPLES_PER_CLASS),    # attention_val
    np.random.randint(8, 15, NUM_SAMPLES_PER_CLASS)       # interaction_rate
])

X = np.vstack([idle_features, passive_features, studying_features])
y = np.array(
    ["idle"]*NUM_SAMPLES_PER_CLASS +
    ["passive"]*NUM_SAMPLES_PER_CLASS +
    ["studying"]*NUM_SAMPLES_PER_CLASS
)

# -----------------------------
# Split dataset
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# -----------------------------
# Train XGBoost classifier
# -----------------------------
clf = XGBClassifier(use_label_encoder=False, eval_metric='mlogloss')
clf.fit(X_train, y_train)

# -----------------------------
# Evaluate
# -----------------------------
y_pred = clf.predict(X_test)
print(classification_report(y_test, y_pred))

# -----------------------------
# Save model & label map
# -----------------------------
with open("core/intent_classifier.pkl", "wb") as f:
    pickle.dump(clf, f)

label_map = {i: cls for i, cls in enumerate(clf.classes_)}
with open("core/intent_label_map.pkl", "wb") as f:
    pickle.dump(label_map, f)

print("Intent classifier and label map saved successfully!")
