#core/audio_module.py
import os
import logging
import pickle
import numpy as np
import sounddevice as sd
import librosa
from threading import Thread, Event
from typing import Dict, Optional

# -----------------------------
# Logging setup
# -----------------------------
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/audio_module.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------------
# Audio Settings
# -----------------------------
SAMPLE_RATE = 16000
DURATION = 5  # seconds per clip
CLF_PATH = "core/audio_classifier.pkl"

# -----------------------------
# Audio Module Class
# -----------------------------
class AudioModule:
    def __init__(self, sample_rate=SAMPLE_RATE, duration=DURATION, clf_path=CLF_PATH):
        self.sample_rate = sample_rate
        self.duration = duration
        self.clf_path = clf_path
        self.clf = self.load_classifier()
        self.latest_audio = np.zeros(int(self.sample_rate * self.duration))
        self.latest_result: Dict[str, any] = {}
        self._stop_event = Event()
        self.thread: Optional[Thread] = None

    def load_classifier(self):
        if os.path.exists(self.clf_path):
            try:
                with open(self.clf_path, "rb") as f:
                    clf = pickle.load(f)
                logger.info("Audio classifier loaded successfully.")
                return clf
            except Exception:
                logger.exception("Failed to load audio classifier.")
        else:
            logger.warning("Audio classifier not found; using default labels.")
        return None

    def record_audio(self) -> np.ndarray:
        """Record audio from default microphone safely."""
        try:
            audio = sd.rec(int(self.duration * self.sample_rate), samplerate=self.sample_rate, channels=1)
            sd.wait()
            return audio.flatten()
        except Exception:
            logger.exception("Audio recording failed; returning zeros.")
            return np.zeros(int(self.duration * self.sample_rate))

    def extract_features(self, audio: np.ndarray) -> np.ndarray:
        """Compute MFCC + energy."""
        try:
            audio = np.array(audio, dtype=float)
            if np.all(audio == 0):
                return np.zeros(14)
            mfccs = librosa.feature.mfcc(y=audio, sr=self.sample_rate, n_mfcc=13)
            mfccs_mean = np.mean(mfccs, axis=1)
            energy = np.mean(audio ** 2)
            return np.concatenate([mfccs_mean, [energy]])
        except Exception:
            logger.exception("Audio feature extraction failed; returning zeros.")
            return np.zeros(14)

    def classify_audio(self, audio: np.ndarray) -> Dict[str, any]:
        """Predict attention state based on audio features."""
        result = {
            "attentive": None,
            "confidence": 0.0,
            "reason": "Unknown",
            "intention": "Observing task",
            "audio_label": "unknown"
        }

        try:
            features = self.extract_features(audio).reshape(1, -1)
            if self.clf:
                label = self.clf.predict(features)[0]
                proba = float(max(self.clf.predict_proba(features)[0]))
                result["audio_label"] = label
                result["confidence"] = proba
                label_map = {
                    "clear_speech": (True, "Clear speech detected"),
                    "speaking": (True, "Clear speech detected"),
                    "silence": (False, "No or very low audio detected"),
                    "low_volume": (False, "No or very low audio detected"),
                    "noise": (False, "Distorted or low-quality audio"),
                    "distortion": (False, "Distorted or low-quality audio"),
                    "muffled": (False, "Distorted or low-quality audio")
                }
                result["attentive"], result["reason"] = label_map.get(label.lower(), (None, f"Ambiguous audio label: {label}"))
            else:
                energy = np.mean(audio ** 2)
                if energy < 1e-4:
                    result.update({"attentive": False, "confidence": 0.5, "reason": "No audio detected"})
                else:
                    result.update({"attentive": True, "confidence": 0.5, "reason": "Audio present, label unknown"})
        except Exception:
            logger.exception("Audio classification failed.")
            result.update({"attentive": False, "confidence": 0.0, "reason": "Classification error"})

        return result

    def audio_pipeline(self) -> Dict[str, any]:
        """Record, classify, and return structured result."""
        self.latest_audio = self.record_audio()
        self.latest_result = self.classify_audio(self.latest_audio)
        logger.info(f"Audio pipeline result: {self.latest_result}")
        return self.latest_result

    # -----------------------------
    # Async continuous pipeline
    # -----------------------------
    def start_async(self):
        if self.thread is None:
            self._stop_event.clear()
            self.thread = Thread(target=self._loop, daemon=True)
            self.thread.start()

    def _loop(self):
        while not self._stop_event.is_set():
            self.audio_pipeline()

    def stop_async(self):
        if self.thread:
            self._stop_event.set()
            self.thread.join()
            self.thread = None

# -----------------------------
# Self-test
# -----------------------------
if __name__ == "__main__":
    audio_module = AudioModule()
    audio_module.start_async()
    import time
    time.sleep(6)  # record one clip asynchronously
    audio_module.stop_async()
    print("Latest result:", audio_module.latest_result)
