import sounddevice as sd
import numpy as np
import librosa
import pickle
import os

# Sampling settings
SAMPLE_RATE = 16000
DURATION = 5  # seconds per clip

# Load or fallback audio classifier
clf_path = "core/audio_classifier.pkl"
if os.path.exists(clf_path):
    with open(clf_path, "rb") as f:
        clf = pickle.load(f)
    print("Audio classifier loaded.")
else:
    clf = None
    print("Audio classifier not found. Using default labels.")

def record_audio(duration=DURATION):
    """Record audio from default microphone safely."""
    try:
        audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
        sd.wait()
        audio = audio.flatten()
        return audio
    except Exception as e:
        print(f"Audio recording failed: {e}")
        return np.zeros(int(duration * SAMPLE_RATE))  # silent fallback

def extract_features(audio):
    """Compute MFCC + energy safely."""
    try:
        if not isinstance(audio, np.ndarray):
            audio = np.array(audio, dtype=float)
        mfccs = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=13)
        mfccs_mean = np.mean(mfccs, axis=1)
        energy = np.mean(audio**2)
        return np.concatenate([mfccs_mean, [energy]])
    except Exception as e:
        print(f"Audio feature extraction failed: {e}")
        return np.zeros(14)  # default feature vector

def classify_audio(audio):
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
        print(f"Audio classification failed: {e}")
        return "unknown", 0.0

def audio_pipeline():
    audio = record_audio()
    label, confidence = classify_audio(audio)
    return {"audio_label": label, "confidence": confidence}

if __name__ == "__main__":
    result = audio_pipeline()
    print("Audio label:", result['audio_label'], "Confidence:", result['confidence'])
