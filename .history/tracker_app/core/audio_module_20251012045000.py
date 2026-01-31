"""
Audio Module (IEEE-Ready v3)
-----------------------------
- Robust audio capture with fallback
- Feature extraction (MFCC + energy)
- Scenario-based attentiveness classification
- Returns structured outputs for multi-modal integration
"""

import sounddevice as sd
import numpy as np
import librosa
import pickle
import os
import logging
from typing import Dict, Optional

# -----------------------------
# LOGGER SETUP
# -----------------------------
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/audio_module.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------------
# SAMPLING SETTINGS
# -----------------------------
SAMPLE_RATE: int = 16000
DURATION: int = 5  # seconds per clip

# -----------------------------
# LOAD AUDIO CLASSIFIER
# -----------------------------
clf_path = "core/audio_classifier.pkl"
clf: Optional[any] = None
if os.path.exists(clf_path):
    try:
        with open(clf_path, "rb") as f:
            clf = pickle.load(f)
        logger.info("Audio classifier loaded successfully.")
    except Exception:
        logger.exception("Failed to load audio classifier.")
else:
    logger.warning("Audio classifier not found; using default labels.")

# -----------------------------
# AUDIO CAPTURE
# -----------------------------
def record_audio(duration: int = DURATION) -> np.ndarray:
    """Record audio from default microphone safely."""
    try:
        audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
        sd.wait()
        return audio.flatten()
    except Exception:
        logger.exception("Audio recording failed; returning zeros.")
        return np.zeros(int(duration * SAMPLE_RATE))

# -----------------------------
# FEATURE EXTRACTION
# -----------------------------
def extract_features(audio: np.ndarray) -> np.ndarray:
    """Compute MFCC + energy safely."""
    try:
        audio = np.array(audio, dtype=float)
        if np.all(audio == 0):
            return np.zeros(14)
        mfccs = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=13)
        mfccs_mean = np.mean(mfccs, axis=1)
        energy = np.mean(audio ** 2)
        return np.concatenate([mfccs_mean, [energy]])
    except Exception:
        logger.exception("Audio feature extraction failed; returning zeros.")
        return np.zeros(14)

# -----------------------------
# AUDIO SCENARIO CLASSIFICATION
# -----------------------------
def classify_audio(audio: np.ndarray) -> Dict[str, any]:
    """Predict attention state based on audio features."""
    result = {
        "attentive": None,
        "confidence": 0.0,
        "reason": "Unknown",
        "intention": "Observing task",
        "audio_label": "unknown"
    }

    try:
        features = extract_features(audio).reshape(1, -1)
        if clf:
            label = clf.predict(features)[0]
            proba = float(max(clf.predict_proba(features)[0]))
            result["audio_label"] = label
            result["confidence"] = proba

            # Map label to attentive scenarios
            if label.lower() in ["clear_speech", "speaking"]:
                result.update({"attentive": True, "reason": "Clear speech detected"})
            elif label.lower() in ["silence", "low_volume"]:
                result.update({"attentive": False, "reason": "No or very low audio detected"})
            elif label.lower() in ["noise", "distortion", "muffled"]:
                result.update({"attentive": False, "reason": "Distorted or low-quality audio"})
            else:
                result.update({"attentive": None, "reason": f"Ambiguous audio label: {label}"})
        else:
            # Fallback if classifier missing
            energy = np.mean(audio**2)
            if energy < 1e-4:
                result.update({"attentive": False, "confidence": 0.5, "reason": "No audio detected"})
            else:
                result.update({"attentive": True, "confidence": 0.5, "reason": "Audio present, label unknown"})
    except Exception as e:
        logger.exception(f"Audio classification failed: {e}")
        result.update({"attentive": False, "confidence": 0.0, "reason": "Classification error"})

    return result

# -----------------------------
# AUDIO PIPELINE
# -----------------------------
def audio_pipeline() -> Dict[str, any]:
    """Record, classify, and return structured audio attentiveness."""
    audio = record_audio()
    result = classify_audio(audio)
    logger.info(f"Audio pipeline result: {result}")
    return result

# -----------------------------
# SELF-TEST
# -----------------------------
if __name__ == "__main__":
    result = audio_pipeline()
    print("Audio pipeline output:")
    print(result)
