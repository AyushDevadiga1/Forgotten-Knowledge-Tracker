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
def _get_env_float(var_name: str, default: float) -> float:
    """Safely parse float env vars with fallback."""
    try:
        value = float(os.getenv(var_name, default))
        if value <= 0:
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
if not os.path.exists(os.path.dirname(DB_PATH)):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    logging.info(f"Created missing database directory at {os.path.dirname(DB_PATH)}")

if not os.path.isfile(TESSERACT_PATH):
    logging.warning(f"Tesseract executable not found at {TESSERACT_PATH}. "
                    "Ensure it's correctly installed and path is updated.")
