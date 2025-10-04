# Tracker intervals (in seconds)
TRACK_INTERVAL = 2
SCREENSHOT_INTERVAL = 10
AUDIO_INTERVAL = 5
WEBCAM_INTERVAL = 30 # seconds
USER_ALLOW_WEBCAM = False  # toggle on/off

# Paths
DB_PATH = "./data/sessions.db"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Update based on your install

# -----------------------------
# Fernet Encryption Key
# -----------------------------
# Load from existing key in data folder
from cryptography.fernet import Fernet
import os


    ENCRYPTION_KEY = 6BjL-JHOB0KXWtvEk0QXwJ4vrduC7YnI87sqHIphPKE"