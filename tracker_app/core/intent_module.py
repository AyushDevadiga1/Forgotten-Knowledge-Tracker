# core/intent_module.py
import numpy as np
import pickle
import os
from typing import Union, List, Dict

# -------------------------------
# Load trained intent classifier
# -------------------------------
clf_path = "core/intent_classifier.pkl"
map_path = "core/intent_label_map.pkl"

intent_clf = None
intent_label_map = None

if os.path.exists(clf_path):
    try:
        with open(clf_path, "rb") as f:
            intent_clf = pickle.load(f)
        print("Intent classifier loaded.")
    except Exception as e:
        print(f"[IntentModule] Failed to load classifier: {e}")

if os.path.exists(map_path):
    try:
        with open(map_path, "rb") as f:
            intent_label_map = pickle.load(f)
        print("Intent label map loaded.")
    except Exception as e:
        print(f"[IntentModule] Failed to load label map: {e}")

# -------------------------------
# Feature extraction
# -------------------------------
def extract_features(
    ocr_keywords: Union[List[str], Dict[str, float]],
    audio_label: str,
    attention_score: float,
    interaction_rate: float,
    use_webcam: bool = False
) -> np.ndarray:
    """
    Convert multi-modal data into numerical features safely.
    """
    try:
        # OCR features
        if not isinstance(ocr_keywords, (list, dict)):
            ocr_keywords = {}
        ocr_val = len(ocr_keywords)

        # Audio features mapping
        audio_map = {"speech": 2, "music": 1, "silence": 0}
        audio_val = audio_map.get(audio_label, 0)

        # Attention & interaction
        att_val = int(attention_score) if use_webcam else 50
        interaction_val = int(interaction_rate)

        features = np.array([ocr_val, audio_val, att_val, interaction_val]).reshape(1, -1)
        return features

    except Exception as e:
        print(f"[IntentModule] Feature extraction failed: {e}")
        return np.array([[0, 0, 50, 0]])

# -------------------------------
# Intent prediction
# -------------------------------
def predict_intent(
    ocr_keywords: Union[List[str], Dict[str, float]],
    audio_label: str,
    attention_score: float,
    interaction_rate: float,
    use_webcam: bool = False
) -> Dict[str, Union[str, float]]:
    """
    Predict intent using trained classifier or fallback rules safely.
    """
    try:
        # Extract features
        features = extract_features(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam)

        # -------------------------------
        # Use classifier if available
        # -------------------------------
        if intent_clf:
            pred = intent_clf.predict(features)[0]

            # Convert numeric label to string using LabelEncoder
            if intent_label_map and not isinstance(pred, str):
                label = intent_label_map.inverse_transform([pred])[0]
            else:
                label = str(pred)

            # Confidence from classifier probabilities
            confidence = float(max(intent_clf.predict_proba(features)[0]))
            return {"intent_label": label, "confidence": confidence}

        # -------------------------------
        # Fallback rules
        # -------------------------------
        if audio_label == "speech" and interaction_rate > 5:
            if use_webcam and attention_score > 50:
                return {"intent_label": "studying", "confidence": 0.8}
            else:
                return {"intent_label": "passive", "confidence": 0.6}
        elif interaction_rate < 2:
            return {"intent_label": "idle", "confidence": 0.7}
        else:
            return {"intent_label": "passive", "confidence": 0.6}

    except Exception as e:
        print(f"[IntentModule] Intent prediction failed: {e}")
        return {"intent_label": "unknown", "confidence": 0.0}

# -------------------------------
# Self-test / demo
# -------------------------------
if __name__ == "__main__":
    sample = predict_intent(
        ocr_keywords=["photosynthesis", "chlorophyll"],
        audio_label="speech",
        attention_score=78,
        interaction_rate=10
    )
    print("Predicted Intent:", sample)
