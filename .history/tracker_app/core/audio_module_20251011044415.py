"""
Audio Module (IEEE-Ready v2)
-----------------------------
- Safe audio capture, feature extraction (MFCC + energy)
- Audio classification using pre-trained model
- Logs events to centralized multi-modal database
"""

import sounddevice as sd
import numpy as np
import librosa
import pickle
import os
import logging
from typing import Tuple, Dict, Optional
from core.db_module import log_multi_modal_event

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
# Sampling settings
# -----------------------------
SAMPLE_RATE: int = 16000
DURATION: int = 5  # seconds per clip

# -----------------------------
# Load audio classifier
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
    logger.warning("Audio classifier not found. Using default labels.")

# -----------------------------
# Audio capture
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
# Feature extraction
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
# Classification
# -----------------------------
def classify_audio(audio: np.ndarray) -> Tuple[str, float]:
    """Predict audio label safely and log to DB."""
    label: str = "unknown"
    confidence: float = 0.0
    try:
        if clf:
            features = extract_features(audio).reshape(1, -1)
            label = clf.predict(features)[0]
            confidence = float(max(clf.predict_proba(features)[0]))
    except Exception:
        logger.exception("Audio classification failed; falling back to 'unknown'.")

    # Centralized logging
    try:
        log_multi_modal_event(
            window_title=f"Audio Classification: {label}",
            ocr_keywords=None,
            audio_label=label,
            attention_score=None,
            interaction_rate=None,
            intent_label=None,
            intent_confidence=confidence,
            memory_score=None,
            source_module="AudioModule"
        )
    except Exception:
        logger.exception("Failed to log audio classification event.")

    return label, confidence

# -----------------------------
# Audio pipeline
# -----------------------------
def audio_pipeline() -> Dict[str, float]:
    """Record, classify, and return structured audio result."""
    audio = record_audio()
    label, confidence = classify_audio(audio)
    logger.info(f"Audio classified: {label} (confidence={confidence:.2f})")
    return {"audio_label": label, "confidence": confidence}

# -----------------------------
# SELF-TEST
# -----------------------------
if __name__ == "__main__":
    result = audio_pipeline()
    print(f"Audio label: {result['audio_label']}, Confidence: {result['confidence']:.2f}")
