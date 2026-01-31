# core/audio_module.py
"""
Audio Module
-------------
IEEE-grade enhancement for safe audio capture, feature extraction, and classification.
Supports logging, fallbacks, and integration with multi-modal tracking.
"""

import sounddevice as sd
import numpy as np
import librosa
import pickle
import os
import logging
from typing import Tuple, Dict
from config import DB_PATH

# -----------------------------
# LOGGER SETUP
# -----------------------------
logging.basicConfig(
    filename="logs/audio_module.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -----------------------------
# Sampling settings
# -----------------------------
SAMPLE_RATE = 16000
DURATION = 5  # seconds per clip

# -----------------------------
# Load audio classifier
# -----------------------------
clf_path = "core/audio_classifier.pkl"
clf = None
if os.path.exists(clf_path):
    try:
        with open(clf_path, "rb") as f:
            clf = pickle.load(f)
        logging.info("Audio classifier loaded successfully.")
    except Exception as e:
        logging.error(f"Failed to load audio classifier: {e}")
else:
    logging.warning("Audio classifier not found. Using default labels.")


# -----------------------------
# Audio capture
# -----------------------------
def record_audio(duration: int = DURATION) -> np.ndarray:
    """Record audio from default microphone safely."""
    try:
        audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
        sd.wait()
        return audio.flatten()
    except Exception as e:
        logging.error(f"Audio recording failed: {e}")
        return np.zeros(int(duration * SAMPLE_RATE))


# -----------------------------
# Feature extraction
# -----------------------------
def extract_features(audio: np.ndarray) -> np.ndarray:
    """Compute MFCC + energy safely."""
    try:
        audio = np.array(audio, dtype=float)
        mfccs = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=13)
        mfccs_mean = np.mean(mfccs, axis=1)
        energy = np.mean(audio**2)
        return np.concatenate([mfccs_mean, [energy]])
    except Exception as e:
        logging.error(f"Audio feature extraction failed: {e}")
        return np.zeros(14)


# -----------------------------
# Classification
# -----------------------------
def classify_audio(audio: np.ndarray) -> Tuple[str, float]:
    """Predict audio label safely."""
    try:
        if clf:
            features = extract_features(audio).reshape(1, -1)
            label = clf.predict(features)[0]
            confidence = float(max(clf.predict_proba(features)[0]))
            return label, confidence
        else:
            return "unknown", 0.0
    except Exception as e:
        logging.error(f"Audio classification failed: {e}")
        return "unknown", 0.0


# -----------------------------
# Audio pipeline
# -----------------------------
def audio_pipeline() -> Dict[str, float]:
    """Record, classify, and return structured audio result."""
    audio = record_audio()
    label, confidence = classify_audio(audio)
    logging.info(f"Audio classified: {label} (confidence={confidence:.2f})")
    return {"audio_label": label, "confidence": confidence}


# -----------------------------
# SELF-TEST
# -----------------------------
if __name__ == "__main__":
    result = audio_pipeline()
    print(f"Audio label: {result['audio_label']}, Confidence: {result['confidence']:.2f}")
