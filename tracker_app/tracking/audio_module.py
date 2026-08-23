"""Audio pipeline: async recording, MFCC feature extraction, and classification.

Classification is deterministic heuristics over RMS energy, spectral shape and
syllabic-rate amplitude modulation. FKT previously shipped a "trained"
GaussianNB classifier fed entirely by synthetic random MFCC vectors
(`train_audio_classifier`) — a stub that created a false sense of quality
(see ADR-002). The synthetic trainer and its model-loading path were removed;
the feature-driven heuristic is the honest classifier (C-4).
"""

import threading
import logging
import warnings
from typing import Callable, Optional, Tuple

import numpy as np
import sounddevice as sd
import librosa

warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger("AudioModule")

DURATION = 5
SAMPLE_RATE = 22050

# ─── Thread-safe result cache ─────────────────────────────────────────────────
# loop.py reads this; the background recording thread writes it.
_audio_result_cache: dict = {"audio_label": "silence", "confidence": 0.9}
_audio_lock = threading.Lock()


# ─── MFCC feature extraction ─────────────────────────────────────────────────


def extract_mfcc_features(audio: np.ndarray, sr: int = SAMPLE_RATE, n_mfcc: int = 13) -> np.ndarray:
    """
    39-dimensional MFCC feature vector:
      13 MFCC means + 13 delta means + 13 delta-delta means.
    Returns zeros for silent/near-silent audio.
    """
    if len(audio) == 0 or np.max(np.abs(audio)) < 1e-6:
        return np.zeros(39)
    try:
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=n_mfcc)
        delta = librosa.feature.delta(mfccs)
        delta2 = librosa.feature.delta(mfccs, order=2)
        return np.concatenate(
            [
                np.mean(mfccs, axis=1),
                np.mean(delta, axis=1),
                np.mean(delta2, axis=1),
            ]
        )
    except Exception as e:
        logger.warning(f"MFCC extraction failed: {e}")
        return np.zeros(39)


# ─── Energy-based fallback heuristic ─────────────────────────────────────────

SILENCE_RMS_THRESHOLD = 0.005  # below this the capture is treated as quiet
TONAL_FLATNESS_THRESHOLD = 0.35  # below this the spectrum is harmonic (music)
SPEECH_SYLLABIC_THRESHOLD = 0.90  # above this the envelope is speech-paced

# Syllabic band (Hz): human speech modulates its envelope at 2–8 Hz (syllables).
SYLLABIC_BAND = (1.0, 8.0)


def _syllabic_modulation(audio: np.ndarray, sr: int = SAMPLE_RATE) -> float:
    """Fraction of amplitude-envelope power in the syllabic (1–8 Hz) band.

    Speech (talk radio, lectures, dialog) has strong envelope modulation at
    syllable rates; steady noise, pure tones and slow-breathed music have
    almost none — so this is the feature that keeps white noise from being
    labeled speech. Returns 0.0 on failure or near-silence.
    """
    try:
        if len(audio) == 0 or np.max(np.abs(audio)) < 1e-6:
            return 0.0
        env = np.abs(librosa.stft(audio, hop_length=256)).sum(axis=0)
        env = env - env.mean()
        frame_rate = sr / 256.0
        f = np.fft.rfftfreq(len(env), d=1.0 / frame_rate)
        power = np.abs(np.fft.rfft(env)) ** 2
        total = power.sum() + 1e-12
        return float(power[(f >= SYLLABIC_BAND[0]) & (f <= SYLLABIC_BAND[1])].sum() / total)
    except Exception as e:
        logger.warning(f"Syllabic modulation failed: {e}")
        return 0.0


def energy_based_classification(audio: np.ndarray) -> Tuple[str, float]:
    """Deterministic audio classification from RMS + spectral + modulation.

    Decision order:
      1. Near-silence            -> silence (low RMS)
      2. Tonal / harmonic        -> music   (flatness low: tones, chords, vocals)
      3. Syllabic-rate AM        -> speech  (envelope modulates 2–8 Hz)
      4. Steady, low-brightness  -> music   (ambient hum, pink noise)
      5. Everything else         -> unknown

    The old three-threshold version labeled white noise as speech (high ZCR +
    bright centroid) and low-level noise as speech — both fixed by the
    modulation feature and an explicit silence floor.
    """
    try:
        if len(audio) == 0 or np.max(np.abs(audio)) < 1e-6:
            return "silence", 0.95
        rms = np.sqrt(np.mean(audio**2))
        if rms < SILENCE_RMS_THRESHOLD:
            return "silence", 0.95
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(audio)))
        sc = float(np.mean(librosa.feature.spectral_centroid(y=audio, sr=SAMPLE_RATE)))
        flat = float(np.mean(librosa.feature.spectral_flatness(y=audio)))
        syll = _syllabic_modulation(audio)
        if flat < TONAL_FLATNESS_THRESHOLD:
            return "music", 0.80
        if syll > SPEECH_SYLLABIC_THRESHOLD:
            return "speech", 0.78
        if zcr < 0.15 and sc < 2500:
            return "music", 0.60
        return "unknown", 0.45
    except Exception as e:
        logger.warning(f"Energy classification failed: {e}")
        return "unknown", 0.30


# ─── Classification ───────────────────────────────────────────────────────────


def classify_audio(audio: np.ndarray) -> Tuple[str, float]:
    """Classify audio using deterministic RMS/spectral/modulation heuristics.

    This is the only classifier (see module docstring — the synthetic ML trainer
    and loader were removed per C-4 / ADR-002).
    """
    return energy_based_classification(audio)


# ─── Blocking pipeline (kept for backward compat / direct calls) ──────────────


def record_audio(duration: int = DURATION) -> np.ndarray:
    try:
        audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
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
            audio = record_audio(DURATION)
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


if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO)
    print("Testing async pipeline (5s recording)...")
    audio_pipeline_async()
    time.sleep(7)
    print("Result:", get_cached_audio_result())
