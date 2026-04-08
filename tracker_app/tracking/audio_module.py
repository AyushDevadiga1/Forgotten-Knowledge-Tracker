# tracking/audio_module.py — FKT 2.0 Phase 5
# Changes from v1:
#   - Non-blocking async recording: sd.wait() no longer freezes the main loop
#   - MFCC-based classifier replaces unreliable energy heuristics
#   - Lazy model loading: classifier loads on first call
#   - Thread-safe result cache shared with loop.py

import threading
import logging
import os
import warnings
from typing import Callable, Optional, Tuple

import numpy as np
import sounddevice as sd
import librosa

warnings.filterwarnings('ignore', category=FutureWarning)

logger = logging.getLogger("AudioModule")

DURATION    = 5
SAMPLE_RATE = 22050

# ─── Thread-safe result cache ─────────────────────────────────────────────────
# loop.py reads this; the background recording thread writes it.
_audio_result_cache: dict = {"audio_label": "silence", "confidence": 0.9}
_audio_lock = threading.Lock()

# ─── Lazy classifier ─────────────────────────────────────────────────────────
_clf_model = None
_clf_loaded = False
_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "models", "audio_classifier.pkl"
)


def _load_classifier():
    global _clf_model, _clf_loaded
    if _clf_loaded:
        return _clf_model
    _clf_loaded = True
    try:
        import pickle
        model_path = os.path.abspath(_MODEL_PATH)
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                data = pickle.load(f)
            _clf_model = data["model"]
            logger.info("Audio classifier loaded from disk.")
        else:
            logger.info("Audio classifier not found — using energy heuristics.")
    except Exception as e:
        logger.warning(f"Audio classifier load failed: {e}")
    return _clf_model


# ─── MFCC feature extraction ─────────────────────────────────────────────────

def extract_mfcc_features(audio: np.ndarray, sr: int = SAMPLE_RATE,
                           n_mfcc: int = 13) -> np.ndarray:
    """
    39-dimensional MFCC feature vector:
      13 MFCC means + 13 delta means + 13 delta-delta means.
    Returns zeros for silent/near-silent audio.
    """
    if len(audio) == 0 or np.max(np.abs(audio)) < 1e-6:
        return np.zeros(39)
    try:
        mfccs  = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=n_mfcc)
        delta  = librosa.feature.delta(mfccs)
        delta2 = librosa.feature.delta(mfccs, order=2)
        return np.concatenate([
            np.mean(mfccs,  axis=1),
            np.mean(delta,  axis=1),
            np.mean(delta2, axis=1),
        ])
    except Exception as e:
        logger.warning(f"MFCC extraction failed: {e}")
        return np.zeros(39)


# ─── Energy-based fallback heuristic ─────────────────────────────────────────

def energy_based_classification(audio: np.ndarray) -> Tuple[str, float]:
    """Fallback when classifier unavailable. Uses RMS + ZCR + spectral centroid."""
    try:
        if len(audio) == 0 or np.max(np.abs(audio)) < 1e-6:
            return "silence", 0.95
        rms = np.sqrt(np.mean(audio ** 2))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(audio)))
        sc  = float(np.mean(librosa.feature.spectral_centroid(y=audio, sr=SAMPLE_RATE)))
        if rms < 0.005:
            return "silence", 0.95
        elif zcr > 0.15 and sc > 2000:
            return "speech",  0.78
        elif rms > 0.03 and zcr < 0.1:
            return "music",   0.70
        else:
            return "unknown", 0.50
    except Exception as e:
        logger.warning(f"Energy classification failed: {e}")
        return "unknown", 0.30


# ─── Classification ───────────────────────────────────────────────────────────

def classify_audio(audio: np.ndarray) -> Tuple[str, float]:
    """
    Classify audio using trained MFCC classifier if available,
    falling back to energy heuristics.
    """
    clf = _load_classifier()
    if clf is not None:
        try:
            features = extract_mfcc_features(audio).reshape(1, -1)
            label    = clf.predict(features)[0]
            proba    = clf.predict_proba(features)[0]
            conf     = float(np.max(proba))
            return str(label), conf
        except Exception as e:
            logger.warning(f"Classifier prediction failed: {e} — using heuristic")

    return energy_based_classification(audio)


# ─── Blocking pipeline (kept for backward compat / direct calls) ──────────────

def record_audio(duration: int = DURATION) -> np.ndarray:
    try:
        audio = sd.rec(int(duration * SAMPLE_RATE),
                       samplerate=SAMPLE_RATE, channels=1, dtype='float32')
        sd.wait()
        return audio.flatten()
    except Exception as e:
        logger.warning(f"Audio recording failed: {e}")
        return np.zeros(int(duration * SAMPLE_RATE))


def audio_pipeline() -> dict:
    """Blocking pipeline — used when called synchronously."""
    audio = record_audio()
    label, conf = classify_audio(audio)
    result = {"audio_label": label, "confidence": conf}
    with _audio_lock:
        _audio_result_cache.update(result)
    return result


# ─── Non-blocking async pipeline ─────────────────────────────────────────────

def audio_pipeline_async(callback: Optional[Callable] = None):
    """
    Record and classify audio in a background daemon thread.
    Does NOT block the calling thread.

    When done, updates _audio_result_cache and optionally calls callback(result).
    loop.py should call this and read _audio_result_cache each cycle.
    """
    def _run():
        try:
            audio  = record_audio(DURATION)
            label, conf = classify_audio(audio)
            result = {"audio_label": label, "confidence": conf}
            with _audio_lock:
                _audio_result_cache.update(result)
            if callback:
                callback(result)
            logger.debug(f"Audio (async): {label} ({conf:.2f})")
        except Exception as e:
            logger.warning(f"Async audio pipeline error: {e}")

    t = threading.Thread(target=_run, daemon=True, name="fkt-audio")
    t.start()


def get_cached_audio_result() -> dict:
    """Return the most recent audio classification result (thread-safe)."""
    with _audio_lock:
        return _audio_result_cache.copy()


# ─── Training helper ──────────────────────────────────────────────────────────

def train_audio_classifier(n_per_class: int = 600, seed: int = 42):
    """
    Train and save a lightweight GaussianNB audio classifier.
    Called from scripts/train_models_from_logs.py.
    Generates synthetic MFCC-like feature vectors per class.
    """
    import pickle
    from sklearn.naive_bayes import GaussianNB
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import cross_val_score

    rng = np.random.default_rng(seed)
    X, y = [], []

    for _ in range(n_per_class):
        # Silence — near-zero across all features
        feats = rng.normal(0, 0.05, 39)
        X.append(feats); y.append("silence")

        # Speech — high first MFCC, high delta variance
        feats = rng.normal(0, 1.0, 39)
        feats[0]  = rng.normal(-20, 5)
        feats[1:6] = rng.normal(5, 2, 5)
        feats[13:18] = rng.normal(2, 1.5, 5)  # high delta
        X.append(feats); y.append("speech")

        # Music — periodic energy, moderate delta
        feats = rng.normal(0, 0.5, 39)
        feats[0]  = rng.normal(-15, 3)
        feats[1:4] = rng.normal(3, 1, 3)
        feats[13:16] = rng.normal(0.5, 0.5, 3)  # lower delta than speech
        X.append(feats); y.append("music")

    X_arr = np.array(X)
    y_arr = np.array(y)

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    GaussianNB()),
    ])

    scores = cross_val_score(model, X_arr, y_arr, cv=5, scoring="accuracy")
    logger.info(f"Audio classifier CV: {scores.mean():.4f} ± {scores.std():.4f}")
    model.fit(X_arr, y_arr)

    model_path = os.path.abspath(_MODEL_PATH)
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump({"model": model, "labels": ["silence", "speech", "music"],
                     "model_version": "2.0.0", "n_features": 39}, f)

    size_kb = os.path.getsize(model_path) / 1024
    logger.info(f"Audio classifier saved → {model_path} ({size_kb:.1f} KB)")
    return model


if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.INFO)
    print("Training audio classifier...")
    train_audio_classifier()
    print("\nTesting async pipeline (5s recording)...")
    audio_pipeline_async()
    time.sleep(7)
    print("Result:", get_cached_audio_result())
