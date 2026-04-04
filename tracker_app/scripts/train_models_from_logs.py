# scripts/train_models_from_logs.py — FKT 2.0
# ────────────────────────────────────────────────────────────
# Trains the intent classifier from either:
#   (a) Existing synthetic data in training_data/intent_training_data.json
#   (b) Freshly generated synthetic data (if no file found)
# Saves model to: tracker_app/models/intent_classifier.pkl
#
# Run:
#   python -m tracker_app.scripts.train_models_from_logs
# ────────────────────────────────────────────────────────────

import json
import pickle
import random
import logging
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.metrics import classification_report, accuracy_score

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("TrainIntent")

ROOT          = Path(__file__).parent.parent
DATA_PATH     = ROOT / "training_data" / "intent_training_data.json"
MODEL_PATH    = ROOT / "models" / "intent_classifier.pkl"
MODEL_PATH.parent.mkdir(exist_ok=True)


# ────────────────────────────────────────────────────────────
def generate_synthetic_data(n_studying=900, n_passive=900, n_idle=700,
                            seed=42) -> dict:
    """
    Generate synthetic training samples.
    Feature order: [ocr_keyword_count, audio_val, attention_score,
                    interaction_rate, keyword_avg_score, audio_confidence]
    """
    rng = np.random.default_rng(seed)
    def cl(v,lo,hi): return float(max(lo,min(hi,v)))
    def ri(a,b):     return int(rng.integers(a,b))

    samples = []

    # STUDYING
    for _ in range(n_studying - 100):
        samples.append(([cl(ri(6,20)+rng.normal(0,2),1,25),
                         int(rng.choice([0,2],p=[.35,.65])),
                         cl(rng.normal(78,10),40,100),
                         cl(rng.normal(12,4),4,40),
                         cl(rng.normal(.72,.12),.3,1.0),
                         cl(rng.normal(.85,.08),.5,1.0)], "studying"))
    for _ in range(100):  # music variant
        samples.append(([cl(ri(5,15)+rng.normal(0,2),1,20), 1,
                         cl(rng.normal(70,12),40,95),
                         cl(rng.normal(10,4),3,30),
                         cl(rng.normal(.65,.12),.3,1.0),
                         cl(rng.normal(.75,.10),.4,1.0)], "studying"))

    # PASSIVE
    for _ in range(n_passive - 100):
        samples.append(([cl(ri(2,10)+rng.normal(0,2),0,15),
                         int(rng.choice([0,1,2],p=[.40,.45,.15])),
                         cl(rng.normal(50,15),15,80),
                         cl(rng.normal(4,2.5),0,15),
                         cl(rng.normal(.45,.15),.1,.85),
                         cl(rng.normal(.70,.12),.4,1.0)], "passive"))
    for _ in range(100):
        samples.append(([cl(ri(3,12)+rng.normal(0,2),0,18),
                         int(rng.choice([1,2],p=[.6,.4])),
                         cl(rng.normal(55,15),20,85),
                         cl(rng.normal(6,3),1,18),
                         cl(rng.normal(.40,.15),.1,.80),
                         cl(rng.normal(.72,.10),.4,1.0)], "passive"))

    # IDLE
    for _ in range(n_idle):
        samples.append(([cl(ri(0,5)+rng.normal(0,1.5),0,8),
                         int(rng.choice([0,1,2],p=[.55,.30,.15])),
                         cl(rng.normal(25,15),0,55),
                         cl(rng.normal(.8,.8),0,4),
                         cl(rng.normal(.20,.15),0,.55),
                         cl(rng.normal(.60,.15),.2,1.0)], "idle"))

    random.shuffle(samples)
    X = [[round(float(f),4) for f in s[0]] for s in samples]
    y = [s[1] for s in samples]

    return {
        "feature_names": ["ocr_keyword_count","audio_val","attention_score",
                          "interaction_rate","keyword_avg_score","audio_confidence"],
        "labels": ["studying","passive","idle"],
        "total_samples": len(samples),
        "class_counts": {l: y.count(l) for l in ["studying","passive","idle"]},
        "X": X, "y": y
    }


# ────────────────────────────────────────────────────────────
def train(data: dict) -> dict:
    X = np.array(data["X"])
    y = np.array(data["y"])

    logger.info(f"Dataset: {len(X)} samples | "
                f"studying={data['class_counts']['studying']} "
                f"passive={data['class_counts']['passive']} "
                f"idle={data['class_counts']['idle']}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        ))
    ])

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy")
    logger.info(f"5-fold CV accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    logger.info(f"Test accuracy: {acc:.4f}")
    print(classification_report(y_test, y_pred,
                                target_names=["idle","passive","studying"]))

    importances = model.named_steps["clf"].feature_importances_
    print("Feature importances:")
    for name, imp in sorted(zip(data["feature_names"], importances),
                            key=lambda x: -x[1]):
        print(f"  {name:<22} {imp:.4f}  {'\u2588'*int(imp*40)}")

    return {
        "model": model,
        "feature_names": data["feature_names"],
        "labels": data["labels"],
        "cv_mean": float(cv_scores.mean()),
        "cv_std":  float(cv_scores.std()),
        "test_accuracy": float(acc),
        "n_training_samples": int(len(X_train)),
        "model_version": "2.0.0"
    }


# ────────────────────────────────────────────────────────────
def main():
    if DATA_PATH.exists():
        logger.info(f"Loading existing training data from {DATA_PATH}")
        with open(DATA_PATH) as f:
            data = json.load(f)
    else:
        logger.info("No training data found. Generating synthetic dataset...")
        data = generate_synthetic_data()
        DATA_PATH.parent.mkdir(exist_ok=True)
        with open(DATA_PATH, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved training data → {DATA_PATH}")

    model_data = train(data)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model_data, f)

    size_kb = MODEL_PATH.stat().st_size / 1024
    logger.info(f"Model saved → {MODEL_PATH} ({size_kb:.1f} KB)")
    logger.info("Done. Restart the tracker to pick up the new model.")


if __name__ == "__main__":
    main()
