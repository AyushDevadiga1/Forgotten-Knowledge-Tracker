# config.py - FIXED VERSION
import os

# Create data directory if it doesn't exist
os.makedirs("./data", exist_ok=True)
os.makedirs("./models", exist_ok=True)

# Tracker intervals (in seconds)
TRACK_INTERVAL = 2
SCREENSHOT_INTERVAL = 10
AUDIO_INTERVAL = 5
WEBCAM_INTERVAL = 30  # seconds

# Paths
DB_PATH = "./data/sessions.db"
ENHANCED_DB_PATH = "./data/enhanced_sessions.db"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Privacy and module settings
USER_CONSENT = False
OCR_ENABLED = True
AUDIO_ENABLED = False
WEBCAM_ENABLED = False
USER_ALLOW_WEBCAM = False

# Data retention
RETENTION_DAYS = 30

# Encryption
ENCRYPTION_ENABLED = False  # Simplified for demo

# SM-2 parameters
SM2_INITIAL_EASE = 2.5
SM2_MINIMUM_EASE = 1.3

# PII Redaction settings
REDACT_EMAILS = True
REDACT_PHONES = True
REDACT_CREDIT_CARDS = True
BLUR_FACES = True

# Study app targeting
STUDY_APPS = ["chrome", "firefox", "edge", "browser", "word", "pdf", "notepad", 
              "visual studio", "pycharm", "vscode", "jupyter"]
ENTERTAINMENT_APPS = ["youtube", "netflix", "spotify", "game", "steam"]

# Algorithm toggles
USE_NOVEL_ALGORITHMS = True
USE_ADVANCED_MEMORY_MODEL = True
USE_ADVANCED_INTENT_CLASSIFIER = True

MEMORY_MODEL_PATH = "./models/memory_model.pth"
INTENT_MODEL_PATH = "./models/intent_classifier.pth"

# Enhanced algorithm parameters
NOVEL_MEMORY_HIDDEN_DIM = 256
NOVEL_INTENT_HIDDEN_DIM = 64
CROSS_MODAL_ATTENTION_HEADS = 4

# Adaptive settings
ADAPTIVE_MEMORY_THRESHOLD = True
CONTEXT_AWARE_SCHEDULING = True

MEMORY_THRESHOLD = 0.6