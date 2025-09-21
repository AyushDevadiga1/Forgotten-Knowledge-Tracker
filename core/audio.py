# Phase 3: audio
import sounddevice as sd
import numpy as np
from scipy.fft import fft
from sklearn.ensemble import RandomForestClassifier
import sqlite3
from config import DB_PATH, AUDIO_CLIP_DURATION

# Placeholder: Pre-trained classifier (in production, train on your own data)
clf = RandomForestClassifier()

def record_audio(duration=AUDIO_CLIP_DURATION, fs=16000):
    print("[Audio] Recording...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    audio = audio.flatten()
    return audio

def extract_features(audio, fs=16000):
    # Simple feature: energy + spectral centroid
    energy = np.sum(audio ** 2) / len(audio)
    fft_vals = np.abs(fft(audio))
    freqs = np.fft.fftfreq(len(audio), 1/fs)
    spectral_centroid = np.sum(freqs * fft_vals) / np.sum(fft_vals + 1e-10)
    return np.array([energy, spectral_centroid]).reshape(1, -1)

def classify_audio(audio):
    features = extract_features(audio)
    # For now, simple threshold rule (later replace with trained classifier)
    energy = features[0][0]
    if energy < 1e-4:
        label = "silence"
        confidence = 0.9
    else:
        label = "speech"  # placeholder
        confidence = 0.8
    return label, confidence

def log_audio(session_id, label, confidence):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO audio_logs (session_id, audio_label, confidence) VALUES (?, ?, ?)",
        (session_id, label, confidence)
    )
    conn.commit()
    conn.close()
