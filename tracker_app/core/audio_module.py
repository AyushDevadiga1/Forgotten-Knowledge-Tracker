import sounddevice as sd
import numpy as np
import librosa
from sklearn.ensemble import RandomForestClassifier
import pickle

# Sampling settings
SAMPLE_RATE = 16000
DURATION = 5  # seconds per clip

# Load or train a simple classifier
try:
    clf = pickle.load(open("core/audio_classifier.pkl", "rb"))
except:
    clf = None
    print("Audio classifier not found. Please train one or use default labels.")

def record_audio(duration=DURATION):
    """Record audio from default microphone"""
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
    sd.wait()
    audio = audio.flatten()
    return audio

def extract_features(audio):
    """Compute MFCC + energy"""
    mfccs = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=13)
    mfccs_mean = np.mean(mfccs, axis=1)
    energy = np.mean(audio**2)
    return np.concatenate([mfccs_mean, [energy]])

def classify_audio(audio):
    """Predict audio label"""
    if clf:
        features = extract_features(audio).reshape(1, -1)
        label = clf.predict(features)[0]
        confidence = max(clf.predict_proba(features)[0])
        return label, confidence
    else:
        return "unknown", 0.0

def audio_pipeline():
    audio = record_audio()
    label, confidence = classify_audio(audio)
    return {"audio_label": label, "confidence": confidence}

if __name__ == "__main__":
    result = audio_pipeline()
    print("Audio label:", result['audio_label'], "Confidence:", result['confidence'])
