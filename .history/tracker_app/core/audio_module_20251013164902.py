# ==========================================================
# core/audio_module.py | FKT v4.0 Async & Multi-Modal
# ==========================================================

import os
import logging
import pickle
import numpy as np
import sounddevice as sd
import librosa
from threading import Thread, Event
from typing import Dict, Optional, Any
import asyncio
from datetime import datetime
from core import memory_model
from core.knowledge_graph import get_graph

# ----------------------------- Logger Setup -----------------------------
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("AudioModule")
if not logger.handlers:
    handler = logging.FileHandler("logs/audio_module.log")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ----------------------------- Audio Settings -----------------------------
SAMPLE_RATE = 16000
DURATION = 5  # seconds per clip
CLF_PATH = "core/audio_classifier.pkl"
FEATURE_DIM = 14  # 13 MFCCs + energy

# ----------------------------- Audio Module -----------------------------
class AudioModule:
    def __init__(self, sample_rate: int = SAMPLE_RATE, duration: int = DURATION, clf_path: str = CLF_PATH):
        self.sample_rate = sample_rate
        self.duration = duration
        self.clf_path = clf_path
        self.clf = self._load_classifier()
        self.latest_audio: np.ndarray = np.zeros(int(self.sample_rate * self.duration))
        self.latest_result: Dict[str, Any] = {}
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

    # ----------------------------- Classifier -----------------------------
    def _load_classifier(self) -> Optional[Any]:
        if os.path.exists(self.clf_path):
            try:
                with open(self.clf_path, "rb") as f:
                    clf = pickle.load(f)
                logger.info("Audio classifier loaded successfully.")
                return clf
            except Exception:
                logger.exception("Failed to load audio classifier.")
        else:
            logger.warning("Audio classifier not found; using default heuristic labels.")
        return None

    # ----------------------------- Recording -----------------------------
    def record_audio(self) -> np.ndarray:
        try:
            audio = sd.rec(int(self.duration * self.sample_rate), samplerate=self.sample_rate, channels=1)
            sd.wait()
            return audio.flatten()
        except Exception:
            logger.exception("Audio recording failed; returning zeros.")
            return np.zeros(int(self.duration * self.sample_rate))

    # ----------------------------- Feature Extraction -----------------------------
    def extract_features(self, audio: np.ndarray) -> np.ndarray:
        try:
            audio = np.array(audio, dtype=float)
            if np.all(audio == 0):
                return np.zeros(FEATURE_DIM)
            mfccs = librosa.feature.mfcc(y=audio, sr=self.sample_rate, n_mfcc=13)
            energy = np.mean(audio ** 2)
            return np.concatenate([np.mean(mfccs, axis=1), [energy]])
        except Exception:
            logger.exception("Audio feature extraction failed; returning zeros.")
            return np.zeros(FEATURE_DIM)

    # ----------------------------- Classification -----------------------------
    def classify_audio(self, audio: np.ndarray) -> Dict[str, Any]:
        result = {
            "attentive": None,
            "confidence": 0.0,
            "reason": "Unknown",
            "intention": "Observing task",
            "audio_label": "unknown",
            "memory_score": 0.0,
            "next_review_time": None,
            "timestamp": datetime.now().isoformat()
        }

        try:
            features = self.extract_features(audio).reshape(1, -1)
            if self.clf:
                label = self.clf.predict(features)[0]
                confidence = float(max(self.clf.predict_proba(features)[0]))
                result.update({"audio_label": label, "confidence": confidence})
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
                result.update({
                    "attentive": energy > 1e-4,
                    "confidence": 0.5,
                    "reason": "Audio detected" if energy > 1e-4 else "No audio detected",
                    "audio_label": "speech" if energy > 1e-4 else "silence"
                })
        except Exception:
            logger.exception("Audio classification failed.")
            result.update({"attentive": False, "confidence": 0.0, "reason": "Classification error"})

        # ----------------- Memory Integration -----------------
        now = datetime.now()
        memory_score = memory_model.compute_memory_score(now, lambda_val=0.1)
        next_review_time = memory_model.schedule_next_review(now, memory_score, lambda_val=0.1)
        result["memory_score"] = memory_score
        result["next_review_time"] = next_review_time.isoformat()
        result["timestamp"] = now.isoformat()

        # ----------------- Knowledge Graph Update -----------------
        try:
            G = get_graph()
            node_name = "audio_event"
            if node_name not in G.nodes:
                G.add_node(
                    node_name,
                    memory_score=memory_score,
                    next_review_time=next_review_time,
                    last_seen_ts=now.isoformat(),
                    count=1
                )
            else:
                node = G.nodes[node_name]
                node['memory_score'] = memory_score
                node['next_review_time'] = next_review_time
                node['last_seen_ts'] = now.isoformat()
                node['count'] += 1
        except Exception as e:
            logger.warning(f"KG update failed for audio_event: {e}")

        return result

    # ----------------------------- Pipeline -----------------------------
    def audio_pipeline(self) -> Dict[str, Any]:
        self.latest_audio = self.record_audio()
        self.latest_result = self.classify_audio(self.latest_audio)
        logger.info(f"Audio pipeline result: {self.latest_result}")
        return self.latest_result

    # ----------------------------- Async wrapper -----------------------------
    async def async_pipeline(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self.audio_pipeline)

