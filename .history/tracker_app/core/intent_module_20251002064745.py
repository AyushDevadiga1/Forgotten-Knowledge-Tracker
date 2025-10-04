import numpy as np
import pickle
import os

# Load or fallback intent classifier
clf_path = "core/intent_classifier.pkl"
map_path = "core/intent_label_map.pkl"
if os.path.exists(clf_path) and os.path.exists(map_path):
    with open(clf_path, "rb") as f:
        intent_clf = pickle.load(f)
    with open(map_path, "rb") as f:
        intent_label_map = pickle.load(f)
    print("Intent classifier loaded.")
else:
    intent_clf = None
    intent_label_map = None
    print("Intent classifier not found. Using fallback rules.")

def extract_features(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam=False):
    """Convert multi-modal data into numerical features safely."""
    try:
        if not isinstance(ocr_keywords, (list, dict)):
            ocr_keywords = {}
        ocr_val = len(ocr_keywords)

        audio_map = {"speech": 2, "music": 1, "silence": 0}
        audio_val = audio_map.get(audio_label, 0)

        att_val = int(attention_score) if use_webcam else 50
        interaction_val = int(interaction_rate)

        return np.array([ocr_val, audio_val, att_val, interaction_val]).reshape(1, -1)
    except Exception as e:
        print(f"Feature extraction failed: {e}")
        return np.array([[0, 0, 50, 0]])

def predict_intent(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam=False):
    """Predict intent safely with fallback rules."""
    try:
        features = extract_features(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam)
        if intent_clf and intent_label_map:
            idx = int(intent_clf.predict(features)[0])
            confidence = float(max(intent_clf.predict_proba(features)[0]))
            label = intent_label_map[idx]
            return {"intent_label": label, "confidence": confidence}
        else:
            # fallback rules
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
        print(f"Intent prediction failed: {e}")
        return {"intent_label": "unknown", "confidence": 0.0}

if __name__ == "__main__":
    sample = predict_intent(
        ocr_keywords=["photosynthesis", "chlorophyll"],
        audio_label="speech",
        attention_score=78,
        interaction_rate=10
    )
    print(sample)
