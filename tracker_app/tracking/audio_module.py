# core/audio_module.py
import sounddevice as sd
import numpy as np
import librosa
import os
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

# Duration for audio recording (seconds)
DURATION = 5
SAMPLE_RATE = 22050  # librosa default

# ----------------------------
# Audio recording
# ----------------------------
def record_audio(duration=DURATION):
    """Record audio safely"""
    try:
        print(f"[RECORD] Recording audio for {duration}s...")
        audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
        sd.wait()
        audio = audio.flatten()
        return audio
    except Exception as e:
        print(f"[FAIL] Audio recording failed: {e}")
        return np.zeros(int(duration * SAMPLE_RATE))

# ----------------------------
# Audio classification
# ----------------------------
def classify_audio(audio):
    """Predict label with fallback threshold logic"""
    try:
        return energy_based_classification(audio)
    except Exception as e:
        print(f"[FAIL] Audio classification failed: {e}")
        return energy_based_classification(audio)

# ----------------------------
# Energy-based fallback (enhanced)
# ----------------------------
def energy_based_classification(audio):
    try:
        if len(audio) == 0 or np.max(np.abs(audio)) < 1e-6:
            return "silence", 0.95
        rms = np.sqrt(np.mean(audio**2))
        zcr = np.mean(librosa.feature.zero_crossing_rate(audio))
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=audio, sr=SAMPLE_RATE))
        # Heuristic rules
        if rms < 0.005:
            return "silence", 0.95
        elif zcr > 0.15 and spectral_centroid > 2000:
            return "speech", 0.8
        elif rms > 0.03 and zcr < 0.1:
            return "music", 0.7
        else:
            return "unknown", 0.5
    except Exception as e:
        print(f"[FAIL] Energy-based classification failed: {e}")
        return "unknown", 0.3

# ----------------------------
# Audio pipeline
# ----------------------------
def audio_pipeline():
    """Complete audio processing pipeline"""
    try:
        audio_data = record_audio()
        label, confidence = classify_audio(audio_data)
        print(f"[AUDIO] Audio: {label} (confidence: {confidence:.2f})")
        return {"audio_label": label, "confidence": confidence}
    except Exception as e:
        print(f"[FAIL] Audio pipeline failed: {e}")
        return {"audio_label": "unknown", "confidence": 0.0}

# ----------------------------
# Test run
# ----------------------------
if __name__ == "__main__":
    result = audio_pipeline()
    print("Audio label:", result['audio_label'], "Confidence:", result['confidence'])
