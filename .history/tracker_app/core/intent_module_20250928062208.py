import numpy as np
import pandas as pd
from xgboost import XGBClassifier
import pickle
import logging
from config import OCR_ENABLED, AUDIO_ENABLED, WEBCAM_ENABLED
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

# NEW: Advanced Multi-Modal Classifier
class AdvancedIntentClassifier(nn.Module):
    """
    Novel multi-modal intent classifier with transformer fusion
    """
    def __init__(self, input_dim=7, hidden_dim=64, num_classes=3):
        super().__init__()
        
        # Feature processing
        self.feature_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # Self-attention for temporal patterns
        self.attention = nn.MultiheadAttention(hidden_dim, num_heads=2)
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 2, num_classes)
        )
        
    def forward(self, x):
        # Encode features
        encoded = self.feature_encoder(x)
        
        # Apply attention (treat features as sequence)
        attended, _ = self.attention(encoded.unsqueeze(1), encoded.unsqueeze(1), encoded.unsqueeze(1))
        
        # Classify
        logits = self.classifier(attended.squeeze(1))
        return logits

# Initialize advanced classifier
try:
    advanced_classifier = AdvancedIntentClassifier()
    try:
        advanced_classifier.load_state_dict(torch.load('models/intent_classifier.pth', map_location='cpu'))
        logger.info("Loaded pre-trained intent classifier")
    except:
        logger.info("Using untrained advanced intent classifier")
    advanced_classifier.eval()
except Exception as e:
    logger.error(f"Failed to initialize advanced classifier: {e}")
    advanced_classifier = None

# ORIGINAL CODE - PRESERVED
try:
    intent_clf = pickle.load(open("core/intent_classifier.pkl", "rb"))
    logger.info("Original intent classifier loaded successfully")
except:
    intent_clf = None
    logger.warning("Original intent classifier not found. Please train one or create default rules.")

def extract_features(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam=False):
    """
    ORIGINAL: Convert multi-modal data into numerical features
    """
    audio_map = {"speech": 2, "music": 1, "silence": 0}
    audio_val = audio_map.get(audio_label, 0)
    ocr_val = len(ocr_keywords)
    interaction_val = interaction_rate
    att_val = attention_score if use_webcam else 50  # default medium attention if webcam off

    return np.array([ocr_val, audio_val, att_val, interaction_val]).reshape(1, -1)

def predict_intent(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam=False):
    """
    ORIGINAL: Intent prediction function
    """
    features = extract_features(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam)
    
    if intent_clf:
        label = intent_clf.predict(features)[0]
        confidence = max(intent_clf.predict_proba(features)[0])
        return {"intent_label": label, "confidence": confidence}
    else:
        # Rule-based fallback (original rules)
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

# NEW: Enhanced feature extraction for novel classifier
def extract_features_enhanced(ocr_keywords, audio_data, attention_data, interaction_rate, 
                            app_type="unknown", use_webcam=False, ocr_confidence=0.5):
    """
    Enhanced feature extraction with context awareness
    """
    # Extract data from enhanced inputs
    audio_label = audio_data.get('audio_label', 'silence') if isinstance(audio_data, dict) else audio_data
    audio_confidence = audio_data.get('confidence', 0.5) if isinstance(audio_data, dict) else 0.5
    attention_score = attention_data.get('attentiveness_score', 0) if isinstance(attention_data, dict) else attention_data
    
    # Audio encoding with confidence
    audio_map = {"speech": 2, "music": 1, "silence": 0, "disabled": -1}
    audio_val = audio_map.get(audio_label, 0)
    
    # OCR features with module awareness
    if not OCR_ENABLED:
        ocr_val = 0
        ocr_confidence = 0
    else:
        ocr_val = len(ocr_keywords) if ocr_keywords else 0
    
    # Attention features with module awareness
    if not use_webcam or not WEBCAM_ENABLED:
        att_val = 50
    else:
        att_val = attention_score
    
    # Interaction features (normalized)
    interaction_val = min(interaction_rate / 10.0, 1.0)
    
    # App type encoding
    app_map = {"study": 2, "browser": 2, "document": 2, "utility": 1, "entertainment": 0}
    app_val = app_map.get(app_type, 0)
    
    # Enhanced feature vector
    features = np.array([
        ocr_val,           # OCR keyword count
        audio_val,         # Audio context
        att_val / 100.0,   # Normalized attention
        interaction_val,   # Normalized interaction
        app_val,           # App type
        ocr_confidence,    # OCR confidence
        audio_confidence   # Audio confidence
    ], dtype=np.float32)
    
    return features

# NEW: Enhanced intent prediction with novel classifier
def predict_intent_enhanced(ocr_keywords, audio_data, attention_data, interaction_rate,
                          app_type="unknown", use_webcam=False, ocr_confidence=0.5):
    """
    Enhanced intent prediction with multi-modal fusion
    """
    # Fallback to original if advanced classifier not available
    if advanced_classifier is None:
        audio_label = audio_data.get('audio_label', 'silence') if isinstance(audio_data, dict) else audio_data
        return predict_intent(ocr_keywords, audio_label, 
                            attention_data.get('attentiveness_score', 0) if isinstance(attention_data, dict) else attention_data,
                            interaction_rate, use_webcam)
    
    try:
        # Extract enhanced features
        features = extract_features_enhanced(
            ocr_keywords, audio_data, attention_data, interaction_rate,
            app_type, use_webcam, ocr_confidence
        )
        
        # Convert to tensor and predict
        features_tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
        
        with torch.no_grad():
            logits = advanced_classifier(features_tensor)
            probabilities = torch.softmax(logits, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
        
        # Map prediction to label
        label_map = {0: "studying", 1: "passive", 2: "idle"}
        intent_label = label_map.get(predicted.item(), "passive")
        
        return {
            "intent_label": intent_label,
            "confidence": confidence.item(),
            "method": "advanced_classifier",
            "features_used": len(features)
        }
        
    except Exception as e:
        logger.error(f"Enhanced intent prediction failed: {e}")
        # Fallback to original
        audio_label = audio_data.get('audio_label', 'silence') if isinstance(audio_data, dict) else audio_data
        return predict_intent(ocr_keywords, audio_label, 
                            attention_data.get('attentiveness_score', 0) if isinstance(attention_data, dict) else attention_data,
                            interaction_rate, use_webcam)

# NEW: Context-aware confidence adjustment
def adjust_confidence_with_context(base_confidence, ocr_conf, audio_conf, app_type, interaction_rate):
    """
    Adjust prediction confidence based on context quality
    """
    adjustment = 0.0
    
    # Boost for strong signals in study context
    if app_type in ["study", "browser", "document"]:
        if ocr_conf > 0.7 and interaction_rate > 3:
            adjustment += 0.15
        elif ocr_conf > 0.5:
            adjustment += 0.08
    
    # Reduce for entertainment context
    if app_type == "entertainment":
        adjustment -= 0.10
    
    # Penalize low-quality signals
    if ocr_conf < 0.3:
        adjustment -= 0.10
    if audio_conf < 0.3:
        adjustment -= 0.05
    
    # Interaction quality bonus
    if 3 <= interaction_rate <= 15:  # Optimal interaction range
        adjustment += 0.05
    
    adjusted_confidence = base_confidence + adjustment
    return max(0.1, min(0.99, adjusted_confidence))

if __name__ == "__main__":
    # Test both systems
    print("Original intent prediction:")
    original_result = predict_intent(
        ocr_keywords=["python", "programming"],
        audio_label="speech",
        attention_score=80,
        interaction_rate=8,
        use_webcam=True
    )
    print(original_result)
    
    print("\nEnhanced intent prediction:")
    enhanced_result = predict_intent_enhanced(
        ocr_keywords=["python", "programming"],
        audio_data={"audio_label": "speech", "confidence": 0.8},
        attention_data={"attentiveness_score": 80},
        interaction_rate=8,
        app_type="browser",
        use_webcam=True,
        ocr_confidence=0.7
    )
    print(enhanced_result)