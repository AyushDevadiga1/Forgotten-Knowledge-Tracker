# core/audio_module.py
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
clf = None

if os.path.exists(clf_path):
    try:
        with open(clf_path, "rb") as f:
            clf = pickle.load(f)
        print("Audio classifier loaded successfully.")
    except Exception as e:
        print(f"Failed to load audio classifier: {e}")
        clf = None
else:
    print("Audio classifier not found. Using energy-based fallback.")

def record_audio(duration=DURATION):
    """Record audio from default microphone safely."""
    try:
        print(f"Recording audio for {duration} seconds...")
        audio = sd.rec(
            int(duration * SAMPLE_RATE), 
            samplerate=SAMPLE_RATE, 
            channels=1, 
            dtype='float64'
        )
        sd.wait()  # Wait for recording to complete
        audio = audio.flatten()
        print(f"Recorded audio: {len(audio)} samples")
        return audio
    except Exception as e:
        print(f"Audio recording failed: {e}")
        # Return silent audio as fallback
        return np.zeros(int(duration * SAMPLE_RATE))

def extract_features(audio):
    """Compute MFCC + energy + spectral features safely."""
    try:
        if not isinstance(audio, np.ndarray) or len(audio) == 0:
            return np.zeros(14)
            
        # Ensure audio is not all zeros (silence)
        if np.max(np.abs(audio)) < 1e-6:
            return np.zeros(14)
            
        # Extract MFCC features
        mfccs = librosa.feature.mfcc(
            y=audio, 
            sr=SAMPLE_RATE, 
            n_mfcc=13,
            n_fft=2048,
            hop_length=512
        )
        mfccs_mean = np.mean(mfccs, axis=1)
        
        # Extract additional features
        energy = np.mean(audio**2)
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=audio, sr=SAMPLE_RATE))
        
        features = np.concatenate([mfccs_mean, [energy, spectral_centroid]])
        return features
        
    except Exception as e:
        print(f"Audio feature extraction failed: {e}")
        return np.zeros(14)  # 13 MFCC + energy + spectral centroid

def classify_audio(audio):
    """Predict audio label safely."""
    try:
        if clf is not None:
            features = extract_features(audio).reshape(1, -1)
            
            # Check if features are valid (not all zeros)
            if np.max(np.abs(features)) < 1e-6:
                return "silence", 0.9
                
            label = clf.predict(features)[0]
            
            # Get confidence from classifier probabilities
            if hasattr(clf, 'predict_proba'):
                probas = clf.predict_proba(features)[0]
                confidence = float(np.max(probas))
            else:
                confidence = 0.7  # Default confidence
                
            return label, confidence
        else:
            # Fallback: energy-based classification
            return energy_based_classification(audio)
            
    except Exception as e:
        print(f"Audio classification failed: {e}")
        return "unknown", 0.0

def energy_based_classification(audio):
    """Simple energy-based audio classification fallback"""
    try:
        if len(audio) == 0:
            return "silence", 0.9
            
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio**2))
        
        # Calculate zero-crossing rate (for speech detection)
        zcr = np.mean(librosa.feature.zero_crossing_rate(audio))
        
        # Simple heuristic classification
        if rms < 0.01:  # Very low energy
            return "silence", 0.9
        elif zcr > 0.1:  # High zero-crossing rate typical of speech
            return "speech", 0.7
        elif rms > 0.05:  # High energy, lower ZCR typical of music
            return "music", 0.6
        else:  # Moderate energy
            return "unknown", 0.5
            
    except Exception as e:
        print(f"Energy-based classification failed: {e}")
        return "unknown", 0.0

def audio_pipeline():
    """Complete audio processing pipeline"""
    try:
        audio_data = record_audio()
        label, confidence = classify_audio(audio_data)
        
        print(f"Audio classification: {label} (confidence: {confidence:.2f})")
        return {"audio_label": label, "confidence": confidence}
        
    except Exception as e:
        print(f"Audio pipeline failed: {e}")
        return {"audio_label": "unknown", "confidence": 0.0}

if __name__ == "__main__":
    result = audio_pipeline()
    print("Audio label:", result['audio_label'], "Confidence:", result['confidence'])