import sounddevice as sd
import numpy as np
import librosa
from sklearn.ensemble import RandomForestClassifier
import pickle
import logging
from config import AUDIO_ENABLED  # NEW

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sampling settings - ORIGINAL
SAMPLE_RATE = 16000
DURATION = 5  # seconds per clip

# Load or train a simple classifier - ORIGINAL
try:
    clf = pickle.load(open("core/audio_classifier.pkl", "rb"))
    logger.info("Audio classifier loaded successfully")
except:
    clf = None
    logger.warning("Audio classifier not found. Please train one or use default labels.")

# NEW: Audio context classification with confidence
def classify_audio_context(audio):
    """
    Enhanced audio classification with context awareness
    Returns: label, confidence, and context features
    """
    if not AUDIO_ENABLED:
        return "disabled", 0.0, {}
    
    if clf:
        features = extract_features(audio).reshape(1, -1)
        label = clf.predict(features)[0]
        confidence = max(clf.predict_proba(features)[0])
        
        # Additional context features
        context_features = extract_audio_context(audio)
        
        return label, confidence, context_features
    else:
        # Enhanced rule-based fallback
        return rule_based_audio_classification(audio)

# NEW: Extract additional audio context features
def extract_audio_context(audio):
    """Extract additional audio features for context awareness"""
    try:
        # Spectral features
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=audio, sr=SAMPLE_RATE))
        spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=audio, sr=SAMPLE_RATE))
        
        # Temporal features
        rms_energy = np.mean(librosa.feature.rms(y=audio))
        zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(audio))
        
        # Voice activity detection (simple threshold)
        voice_activity = 1 if rms_energy > 0.01 else 0
        
        return {
            'spectral_centroid': spectral_centroid,
            'spectral_rolloff': spectral_rolloff,
            'rms_energy': rms_energy,
            'zero_crossing_rate': zero_crossing_rate,
            'voice_activity': voice_activity
        }
    except Exception as e:
        logger.error(f"Error extracting audio context: {e}")
        return {}

# NEW: Enhanced rule-based classification
def rule_based_audio_classification(audio):
    """Enhanced rule-based audio classification with confidence scoring"""
    try:
        features = extract_audio_context(audio)
        rms_energy = features.get('rms_energy', 0)
        spectral_centroid = features.get('spectral_centroid', 0)
        zero_crossing_rate = features.get('zero_crossing_rate', 0)
        
        # Rule-based classification with confidence
        if rms_energy < 0.005:
            return "silence", 0.9, features
        
        elif 1000 < spectral_centroid < 4000 and zero_crossing_rate > 0.1:
            # Likely speech (human voice range)
            confidence = min(rms_energy * 100, 0.8)
            return "speech", confidence, features
        
        elif spectral_centroid > 4000 and rms_energy > 0.01:
            # Likely music (higher frequencies)
            confidence = min(rms_energy * 80, 0.7)
            return "music", confidence, features
        
        else:
            # Unknown or ambient noise
            return "unknown", 0.5, features
            
    except Exception as e:
        logger.error(f"Rule-based classification error: {e}")
        return "unknown", 0.3, {}

# NEW: Privacy-aware audio recording
def record_audio_privacy_aware(duration=DURATION):
    """Audio recording with privacy considerations"""
    if not AUDIO_ENABLED:
        logger.info("Audio recording disabled by user preference")
        return np.zeros(int(duration * SAMPLE_RATE))
    
    try:
        audio = record_audio(duration)
        
        # Apply basic noise reduction (simple high-pass filter)
        audio = butter_highpass_filter(audio, cutoff=80, fs=SAMPLE_RATE)
        
        return audio
    except Exception as e:
        logger.error(f"Audio recording error: {e}")
        return np.zeros(int(duration * SAMPLE_RATE))

# NEW: Simple high-pass filter for noise reduction
def butter_highpass_filter(data, cutoff, fs, order=5):
    """Apply high-pass filter to reduce low-frequency noise"""
    try:
        from scipy.signal import butter, filtfilt
        nyquist = 0.5 * fs
        normal_cutoff = cutoff / nyquist
        b, a = butter(order, normal_cutoff, btype='high', analog=False)
        filtered_data = filtfilt(b, a, data)
        return filtered_data
    except ImportError:
        logger.warning("scipy not available, skipping audio filtering")
        return data
    except Exception as e:
        logger.error(f"Audio filtering error: {e}")
        return data

# ORIGINAL FUNCTIONS - PRESERVED
def record_audio(duration=DURATION):
    """ORIGINAL: Record audio from default microphone"""
    try:
        audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
        sd.wait()
        audio = audio.flatten()
        return audio
    except Exception as e:
        logger.error(f"Audio recording failed: {e}")
        return np.zeros(int(duration * SAMPLE_RATE))

def extract_features(audio):
    """ORIGINAL: Compute MFCC + energy"""
    try:
        mfccs = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=13)
        mfccs_mean = np.mean(mfccs, axis=1)
        energy = np.mean(audio**2)
        return np.concatenate([mfccs_mean, [energy]])
    except Exception as e:
        logger.error(f"Feature extraction error: {e}")
        return np.zeros(14)  # Return zero features on error

def classify_audio(audio):
    """ORIGINAL: Predict audio label"""
    if clf:
        features = extract_features(audio).reshape(1, -1)
        label = clf.predict(features)[0]
        confidence = max(clf.predict_proba(features)[0])
        return label, confidence
    else:
        return "unknown", 0.0

# NEW: Enhanced audio pipeline
def enhanced_audio_pipeline():
    """Enhanced audio processing with context awareness"""
    if not AUDIO_ENABLED:
        return {
            "audio_label": "disabled",
            "confidence": 0.0,
            "context_features": {},
            "recording_duration": 0
        }
    
    try:
        audio = record_audio_privacy_aware()
        
        if np.all(audio == 0):  # Check if recording failed
            return {
                "audio_label": "error",
                "confidence": 0.0,
                "context_features": {},
                "recording_duration": DURATION
            }
        
        label, confidence, context_features = classify_audio_context(audio)
        
        return {
            "audio_label": label,
            "confidence": confidence,
            "context_features": context_features,
            "recording_duration": DURATION,
            "rms_energy": context_features.get('rms_energy', 0),
            "voice_activity": context_features.get('voice_activity', 0)
        }
    except Exception as e:
        logger.error(f"Enhanced audio pipeline error: {e}")
        return {
            "audio_label": "error",
            "confidence": 0.0,
            "context_features": {},
            "recording_duration": DURATION
        }

# ORIGINAL FUNCTION - PRESERVED
def audio_pipeline():
    """ORIGINAL: Audio pipeline without enhancements"""
    try:
        audio = record_audio()
        label, confidence = classify_audio(audio)
        return {"audio_label": label, "confidence": confidence}
    except Exception as e:
        logger.error(f"Audio pipeline error: {e}")
        return {"audio_label": "error", "confidence": 0.0}

# NEW: Audio context analysis for study detection
def analyze_study_context(audio_data, previous_contexts):
    """
    Analyze audio context over time to detect study patterns
    """
    if not audio_data or audio_data.get('audio_label') == 'disabled':
        return {"study_likelihood": 0.0, "pattern": "unknown"}
    
    current_label = audio_data.get('audio_label', 'silence')
    confidence = audio_data.get('confidence', 0.0)
    voice_activity = audio_data.get('voice_activity', 0)
    
    # Simple pattern analysis
    recent_labels = [ctx.get('audio_label', 'silence') for ctx in previous_contexts[-5:]] + [current_label]
    
    # Calculate study likelihood
    study_score = 0.0
    
    # Speech with high confidence suggests lecture/explanation
    if current_label == 'speech' and confidence > 0.7:
        study_score += 0.6
    
    # Silence with occasional speech suggests focused study
    if recent_labels.count('silence') > 3 and current_label == 'speech':
        study_score += 0.3
    
    # Music generally suggests non-study (unless focus music)
    if current_label == 'music':
        study_score -= 0.4
    
    # Voice activity indicates human presence
    if voice_activity:
        study_score += 0.1
    
    study_likelihood = max(0.0, min(1.0, study_score))
    
    # Determine pattern
    if study_likelihood > 0.6:
        pattern = "likely_studying"
    elif study_likelihood > 0.3:
        pattern = "possibly_studying"
    else:
        pattern = "unlikely_studying"
    
    return {
        "study_likelihood": study_likelihood,
        "pattern": pattern,
        "audio_label": current_label,
        "confidence": confidence
    }

if __name__ == "__main__":
    # Test both pipelines
    print("Testing original audio pipeline:")
    result = audio_pipeline()
    print("Original - Label:", result['audio_label'], "Confidence:", result.get('confidence', 0.0))
    
    print("\nTesting enhanced audio pipeline:")
    result_enhanced = enhanced_audio_pipeline()
    print("Enhanced - Label:", result_enhanced['audio_label'])
    print("Enhanced - Confidence:", result_enhanced['confidence'])
    print("Enhanced - Context:", result_enhanced.get('context_features', {}))
    
    # Test study context analysis
    test_contexts = [{"audio_label": "silence", "confidence": 0.9}] * 4
    study_analysis = analyze_study_context(result_enhanced, test_contexts)
    print("Study Analysis:", study_analysis)