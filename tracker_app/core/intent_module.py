# core/intent_module.py
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import os
from typing import Union, List, Dict
from config import INTENT_CLASSIFIER_PATH, INTENT_LABEL_MAP_PATH

# Load trained intent classifier
clf_path = INTENT_CLASSIFIER_PATH
map_path = INTENT_LABEL_MAP_PATH

intent_clf = None
intent_label_map = None

if os.path.exists(clf_path) and os.path.exists(map_path):
    try:
        with open(clf_path, "rb") as f:
            intent_clf = pickle.load(f)
        with open(map_path, "rb") as f:
            intent_label_map = pickle.load(f)
        print("Intent classifier and label map loaded successfully.")
    except Exception as e:
        print(f"[IntentModule] Failed to load classifier: {e}")
        intent_clf = None
        intent_label_map = None
else:
    print("[IntentModule] Classifier files not found, using fallback rules.")

def safe_convert_to_float(value, default=0.0):
    """Safely convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

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
        # OCR features - handle both list and dict
        if isinstance(ocr_keywords, dict):
            ocr_val = len(ocr_keywords)
        elif isinstance(ocr_keywords, list):
            ocr_val = len(ocr_keywords)
        else:
            ocr_val = 0

        # Audio features mapping
        audio_map = {"speech": 2, "music": 1, "silence": 0, "unknown": 0}
        audio_val = audio_map.get(str(audio_label).lower(), 0)

        # Attention & interaction - ensure proper bounds
        att_val = max(0, min(100, safe_convert_to_float(attention_score, 50)))
        if not use_webcam:
            att_val = 50  # Default if webcam not used
            
        interaction_val = max(0, safe_convert_to_float(interaction_rate, 0))

        features = np.array([ocr_val, audio_val, att_val, interaction_val]).reshape(1, -1)
        return features

    except Exception as e:
        print(f"[IntentModule] Feature extraction failed: {e}")
        return np.array([[0, 0, 50, 0]])

def predict_intent(
    ocr_keywords: Union[List[str], Dict[str, float]],
    audio_label: str = "silence",
    attention_score: float = 50,
    interaction_rate: float = 0,
    use_webcam: bool = False
) -> Dict[str, Union[str, float]]:
    """
    Predict intent using trained classifier or fallback rules safely.
    """
    try:
        # Extract features with validation
        features = extract_features(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam)

        # Use classifier if available and properly loaded
        if intent_clf is not None and intent_label_map is not None:
            try:
                pred = intent_clf.predict(features)[0]
                
                # Convert numeric label to string - handle different label_map types
                label = None
                if isinstance(intent_label_map, dict):
                    # Label map is a dictionary: {0: 'studying', 1: 'idle', ...}
                    label = intent_label_map.get(int(pred), str(pred))
                elif hasattr(intent_label_map, 'inverse_transform'):
                    # Label map is a LabelEncoder
                    try:
                        label = intent_label_map.inverse_transform([int(pred)])[0]
                    except (TypeError, ValueError, IndexError) as e:
                        print(f"Error in inverse_transform: {e}, using fallback")
                        label = str(pred)
                else:
                    label = str(pred)
                
                # Ensure label is string
                if label is None:
                    label = "unknown"
                label = str(label).strip()
                
                # Get confidence from classifier probabilities
                if hasattr(intent_clf, 'predict_proba'):
                    try:
                        confidence = float(np.max(intent_clf.predict_proba(features)[0]))
                    except (IndexError, ValueError):
                        confidence = 0.5
                else:
                    confidence = 0.7
                
                return {"intent_label": label, "confidence": confidence}
                
            except Exception as e:
                print(f"[IntentModule] Classifier prediction failed: {e}, using fallback")

        # -------------------------------
        # Fallback rules with improved logic
        # -------------------------------
        interaction_val = safe_convert_to_float(interaction_rate, 0)
        attention_val = safe_convert_to_float(attention_score, 50)
        
        # High interaction + speech + attention = studying
        if (audio_label == "speech" and interaction_val > 5 and 
            (not use_webcam or (use_webcam and attention_val > 60))):
            return {"intent_label": "studying", "confidence": 0.75}
        
        # Low interaction = idle
        elif interaction_val < 2:
            return {"intent_label": "idle", "confidence": 0.7}
            
        # Moderate activity = passive
        else:
            return {"intent_label": "passive", "confidence": 0.6}

    except Exception as e:
        print(f"[IntentModule] Intent prediction failed: {e}")
        return {"intent_label": "unknown", "confidence": 0.0}

if __name__ == "__main__":
    # Test with various inputs
    test_cases = [
        {"ocr": ["photosynthesis", "chlorophyll"], "audio": "speech", "attention": 78, "interaction": 10},
        {"ocr": {}, "audio": "silence", "attention": 20, "interaction": 1},
        {"ocr": ["python", "code"], "audio": "music", "attention": 50, "interaction": 3}
    ]
    
    for i, test in enumerate(test_cases):
        result = predict_intent(
            ocr_keywords=test["ocr"],
            audio_label=test["audio"],
            attention_score=test["attention"],
            interaction_rate=test["interaction"]
        )
        print(f"Test {i+1}: {result}")