# config.py
import os
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Base directory for all data files
DATA_DIR = PROJECT_ROOT / "data"

# Model directory
MODELS_DIR = PROJECT_ROOT / "models"


def setup_directories():
    """Create required directories. Call this from main entry points only.
    NOT called at import time — keeps imports side-effect-free for testing."""
    DATA_DIR.mkdir(exist_ok=True)
    MODELS_DIR.mkdir(exist_ok=True)

# Tracker intervals (in seconds)
TRACK_INTERVAL = 5          # Main tracking loop interval
SCREENSHOT_INTERVAL = 20     # OCR screenshot interval  
AUDIO_INTERVAL = 15           # Audio recording interval
WEBCAM_INTERVAL = 45         # Webcam attention check interval
USER_ALLOW_WEBCAM = True   # Webcam permission toggle

# Database path
DB_PATH = str(DATA_DIR / "sessions.db")

# Tesseract OCR path (update based on your installation)
# Tesseract OCR path (update based on your installation)
def find_tesseract():
    """Find Tesseract executable"""
    import shutil
    
    # Check PATH first
    if shutil.which("tesseract"):
        return "tesseract"
        
    # Check common Windows paths
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\hp\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
            
    return r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Default fallback

TESSERACT_PATH = find_tesseract()

# Model paths (updated to use MODELS_DIR)
INTENT_CLASSIFIER_PATH = str(MODELS_DIR / "intent_classifier.pkl")
INTENT_LABEL_MAP_PATH = str(MODELS_DIR / "intent_label_map.pkl")
AUDIO_CLASSIFIER_PATH = str(MODELS_DIR / "audio_classifier.pkl")
AUDIO_LABEL_ENCODER_PATH = str(MODELS_DIR / "audio_label_encoder.pkl")
AUDIO_SCALER_PATH = str(MODELS_DIR / "audio_scaler.pkl")
KNOWLEDGE_GRAPH_PATH = str(DATA_DIR / "knowledge_graph.pkl")

# Memory model parameters
MEMORY_THRESHOLD = 0.6           # Threshold for review reminders
DEFAULT_LAMBDA = 0.1             # Default memory decay rate
MIN_REVIEW_INTERVAL_HOURS = 1    # Minimum time between reviews
MAX_REVIEW_INTERVAL_HOURS = 720  # Maximum time between reviews (30 days)

# Notification settings
REMINDER_COOLDOWN_HOURS = 1      # Minimum time between reminders for same concept
NOTIFICATION_TIMEOUT = 10        # Notification display time in seconds

# OCR settings
OCR_TOP_KEYWORDS = 15           # Number of keywords to extract
OCR_CONFIDENCE_THRESHOLD = 0.3  # Minimum confidence for keywords

# Audio settings
AUDIO_SAMPLE_RATE = 16000       # Audio sampling rate
AUDIO_DURATION = 5              # Audio clip duration in seconds

# Webcam settings
WEBCAM_FRAME_COUNT = 5          # Number of frames to process for attention
WEBCAM_RESOLUTION = (640, 480)  # Webcam resolution

def validate_config():
    """Validate configuration and check for common issues"""
    issues = []
    
    # Check database directory
    if not DATA_DIR.exists():
        issues.append(f"Data directory does not exist: {DATA_DIR}")
    
    # Check Tesseract
    # Check Tesseract
    is_in_path = TESSERACT_PATH.lower() == "tesseract"
    if is_in_path:
        import shutil
        if not shutil.which("tesseract"):
             issues.append(f"⚠️  WARNING: Tesseract not found in PATH")
             issues.append("   OCR features will not work. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
    elif not os.path.exists(TESSERACT_PATH):
        issues.append(f"⚠️  WARNING: Tesseract not found at: {TESSERACT_PATH}")
        issues.append("   OCR features will not work. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
    
    # Check model files
    model_files = [
        (INTENT_CLASSIFIER_PATH, "Intent classifier"),
        (INTENT_LABEL_MAP_PATH, "Intent label map"), 
        (AUDIO_CLASSIFIER_PATH, "Audio classifier")
    ]
    
    for path, description in model_files:
        if not os.path.exists(path):
            issues.append(f"⚠️  WARNING: {description} not found: {path}")
            issues.append("   Train models using: python train_all_models.py")
    
    # Validate intervals
    intervals = [
        (TRACK_INTERVAL, "TRACK_INTERVAL"),
        (SCREENSHOT_INTERVAL, "SCREENSHOT_INTERVAL"),
        (AUDIO_INTERVAL, "AUDIO_INTERVAL"), 
        (WEBCAM_INTERVAL, "WEBCAM_INTERVAL")
    ]
    
    for value, name in intervals:
        if value <= 0:
            issues.append(f"ERROR: {name} must be positive: {value}")
    
    return issues

def print_config_summary():
    """Print configuration summary"""
    print("=== Configuration Summary ===")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Database: {DB_PATH}")
    print(f"Data Directory: {DATA_DIR}")
    print("\nIntervals (seconds):")
    print(f"  Tracking: {TRACK_INTERVAL}")
    print(f"  Screenshots: {SCREENSHOT_INTERVAL}") 
    print(f"  Audio: {AUDIO_INTERVAL}")
    print(f"  Webcam: {WEBCAM_INTERVAL}")
    print(f"Webcam Enabled: {USER_ALLOW_WEBCAM}")
    print("\nPaths:")
    print(f"  Tesseract: {TESSERACT_PATH}")
    print(f"  Intent Model: {INTENT_CLASSIFIER_PATH}")
    print(f"  Audio Model: {AUDIO_CLASSIFIER_PATH}")
    
    # Validate and show any issues
    issues = validate_config()
    if issues:
        print("\n⚠️  Configuration Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ Configuration validated successfully")

if __name__ == "__main__":
    print_config_summary()