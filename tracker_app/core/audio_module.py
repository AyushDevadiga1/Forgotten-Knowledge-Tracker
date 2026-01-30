# core/audio_module.py
import sounddevice as sd
import numpy as np
import librosa
import pickle
import os

# ----------------------------
# Audio settings (enhanced)
# ----------------------------
SAMPLE_RATE = 22050  # Higher quality
DURATION = 3         # Shorter duration for faster processing

# Load audio classifier
clf_path = "core/audio_classifier.pkl"
clf = None
if os.path.exists(clf_path):
    try:
        with open(clf_path, "rb") as f:
            clf = pickle.load(f)
        print("[OK] Audio classifier loaded successfully.")
    except Exception as e:
        print(f"[FAIL] Failed to load audio classifier: {e}")
        clf = None
else:
    print("[WARN] Audio classifier not found. Using energy-based fallback.")

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
# Feature extraction (enhanced)
# ----------------------------
def extract_features(audio):
    """Compute robust audio features"""
    try:
        if not isinstance(audio, np.ndarray) or len(audio) == 0 or np.max(np.abs(audio)) < 1e-6:
            return np.zeros(20)

        # Pre-emphasis filter
        audio = librosa.effects.preemphasis(audio)

        # MFCCs
        mfccs = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=13, n_fft=2048, hop_length=512)
        mfcc_mean = np.mean(mfccs, axis=1)
        mfcc_std = np.std(mfccs, axis=1)

        # Spectral features
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=audio, sr=SAMPLE_RATE))
        spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=audio, sr=SAMPLE_RATE))
        zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(audio))

        # Energy features
        rms = np.sqrt(np.mean(audio**2))
        energy = np.sum(audio**2)

        # Combine features (20 features)
        features = np.concatenate([
            mfcc_mean,          # 13
            mfcc_std[:2],       # 2
            [spectral_centroid, spectral_rolloff, zero_crossing_rate, rms, energy]  # 5
        ])
        return features[:20]
    except Exception as e:
        print(f"[FAIL] Feature extraction failed: {e}")
        return np.zeros(20)

# ----------------------------
# Audio classification
# ----------------------------
def classify_audio(audio):
    """Predict label with classifier or fallback"""
    try:
        if clf is not None:
            features = extract_features(audio).reshape(1, -1)
            if np.max(np.abs(features)) < 1e-6:
                return "silence", 0.95
            # Check feature shape
            if features.shape[1] != 20:
                return energy_based_classification(audio)
            # Predict
            label = clf.predict(features)[0]
            confidence = float(np.max(clf.predict_proba(features)[0])) if hasattr(clf, 'predict_proba') else 0.7
            return label, confidence
        else:
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
