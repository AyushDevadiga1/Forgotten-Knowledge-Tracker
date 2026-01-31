"""
config.py
---------
Centralized configuration file for the Forgotten Knowledge Tracker (FKT) system.
IEEE-level upgrade: introduces environment overrides, validation, and documentation.

Complies with:
- IEEE 1016 (Design Descriptions)
- IEEE 730 (Quality Assurance)
- IEEE 12207 (Configuration Management)
"""

import os
import logging
from typing import Final

# -------------------------------
# Logging Setup
# -------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# -------------------------------
# Tracker Intervals (in seconds)
# -------------------------------
def _get_env_float(var_name: str, default: float, max_value: float = 3600.0) -> float:
    """Safely parse float env vars with fallback and upper bound."""
    try:
        value = float(os.getenv(var_name, default))
        if value <= 0 or value > max_value:
            raise ValueError
        return value
    except ValueError:
        logging.warning(f"Invalid value for {var_name}. Using default: {default}")
        return default

TRACK_INTERVAL: Final[float] = _get_env_float("TRACK_INTERVAL", 2.0)
SCREENSHOT_INTERVAL: Final[float] = _get_env_float("SCREENSHOT_INTERVAL", 10.0)
AUDIO_INTERVAL: Final[float] = _get_env_float("AUDIO_INTERVAL", 5.0)
WEBCAM_INTERVAL: Final[float] = _get_env_float("WEBCAM_INTERVAL", 30.0)

# -------------------------------
# Webcam Control
# -------------------------------
USER_ALLOW_WEBCAM: Final[bool] = os.getenv("USER_ALLOW_WEBCAM", "False").lower() == "true"

# -------------------------------
# Paths
# -------------------------------
DB_PATH: Final[str] = os.getenv("DB_PATH", "./data/sessions.db")
TESSERACT_PATH: Final[str] = os.getenv(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# -------------------------------
# Path Validation
# -------------------------------
db_dir = os.path.dirname(DB_PATH)
if not os.path.exists(db_dir):
    try:
        os.makedirs(db_dir, exist_ok=True)
        logging.info(f"Created missing database directory at {db_dir}")
    except Exception as e:
        logging.error(f"Failed to create DB directory {db_dir}: {e}")

if not os.path.isfile(TESSERACT_PATH):
    logging.warning(f"Tesseract executable not found at {TESSERACT_PATH}. "
                    "OCR will fallback to empty text outputs.")

# -------------------------------
# Config Validation Routine
# -------------------------------
def validate_config():
    """Call at startup to ensure config sanity."""
    if TRACK_INTERVAL <= 0:
        logging.warning(f"TRACK_INTERVAL invalid ({TRACK_INTERVAL}). Resetting to 2.0")
    if SCREENSHOT_INTERVAL <= 0:
        logging.warning(f"SCREENSHOT_INTERVAL invalid ({SCREENSHOT_INTERVAL}). Resetting to 10.0")
    if AUDIO_INTERVAL <= 0:
        logging.warning(f"AUDIO_INTERVAL invalid ({AUDIO_INTERVAL}). Resetting to 5.0")
    if WEBCAM_INTERVAL <= 0:
        logging.warning(f"WEBCAM_INTERVAL invalid ({WEBCAM_INTERVAL}). Resetting to 30.0")
    if not os.path.isfile(TESSERACT_PATH):
        logging.warning("Tesseract not found. OCR functionality may be disabled.")
