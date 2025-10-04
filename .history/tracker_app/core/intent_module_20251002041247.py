#core/intent_module.py
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
import pickle
# Ensure intent classifier exists
if not os.path.exists(intent_model_path):
    print("Training dummy intent classifier...")
    from xgboost import XGBClassifier
    
    X = np.random.randint(0, 10, size=(50, 4))
    y = np.random.choice(["studying", "idle", "passive"], size=50)
    
    label_map = {"studying": 0, "idle": 1, "passive": 2}
    y_int = np.array([label_map[label] for label in y])
    
    intent_clf = XGBClassifier(use_label_encoder=False, eval_metric='mlogloss')
    intent_clf.fit(X, y_int)
    
    os.makedirs("core", exist_ok=True)
    with open(intent_model_path, "wb") as f:
        pickle.dump(intent_clf, f)
    with open("core/intent_label_map.pkl", "wb") as f:
        pickle.dump(label_map, f)
    
    print("Intent classifier trained and saved.")

# Load or train intent classifier
try:
    intent_clf = pickle.load(open("core/intent_classifier.pkl", "rb"))
except:
    intent_clf = None
    print("Intent classifier not found. Please train one or create default rules.")

def extract_features(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam=False):
    """
    Convert multi-modal data into numerical features
    If webcam is off, attention_score is ignored
    """
    audio_map = {"speech": 2, "music": 1, "silence": 0}
    audio_val = audio_map.get(audio_label, 0)
    ocr_val = len(ocr_keywords)
    interaction_val = interaction_rate
    att_val = attention_score if use_webcam else 50  # default medium attention if webcam off

    return np.array([ocr_val, audio_val, att_val, interaction_val]).reshape(1, -1)

def predict_intent(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam=False):
    features = extract_features(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam)
    
    if intent_clf:
        label = intent_clf.predict(features)[0]
        confidence = max(intent_clf.predict_proba(features)[0])
        return {"intent_label": label, "confidence": confidence}
    else:
        # Rule-based fallback
        if audio_label == "speech" and interaction_rate > 5:
            if use_webcam:
                if attention_score > 50:
                    return {"intent_label": "studying", "confidence": 0.8}
                else:
                    return {"intent_label": "passive", "confidence": 0.6}
            else:
                return {"intent_label": "studying", "confidence": 0.75}
        elif interaction_rate < 2:
            return {"intent_label": "idle", "confidence": 0.7}
        else:
            return {"intent_label": "passive", "confidence": 0.6}

if __name__ == "__main__":
    sample = predict_intent(
        ocr_keywords=["photosynthesis", "chlorophyll"],
        audio_label="speech",
        attention_score=78,
        interaction_rate=10
    )
    print(sample)
