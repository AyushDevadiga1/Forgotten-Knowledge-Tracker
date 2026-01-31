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
logger = logging.getLogger(__name__)

# -------------------------------
# Environment Variable Helpers
# -------------------------------
def _get_env_float(var_name: str, default: float) -> float:
    """Safely parse a float environment variable, using a default if invalid."""
    raw_value = os.getenv(var_name, str(default))
    try:
        value = float(raw_value)
        if value <= 0:
            raise ValueError
        return value
    except (ValueError, TypeError):
        logger.warning(f"Invalid or non-positive value for {var_name}='{raw_value}'. Using default: {default}")
        return default


def _get_env_bool(var_name: str, default: bool) -> bool:
    """Safely parse boolean environment variables."""
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")

# -------------------------------
# Tracker Intervals (in seconds)
# -------------------------------
TRACK_INTERVAL: Final[float] = _get_env_float("TRACK_INTERVAL", 2.0)
SCREENSHOT_INTERVAL: Final[float] = _get_env_float("SCREENSHOT_INTERVAL", 10.0)
AUDIO_INTERVAL: Final[float] = _get_env_float("AUDIO_INTERVAL", 5.0)
WEBCAM_INTERVAL: Final[float] = _get_env_float("WEBCAM_INTERVAL", 30.0)

GRAPH_PATH: Final[str] = os.getenv("GRAPH_PATH", "data/knowledge_graph.pkl")

# -------------------------------
# Webcam Control
# -------------------------------
USER_ALLOW_WEBCAM: Final[bool] = _get_env_bool("USER_ALLOW_WEBCAM", False)

# -------------------------------
# Paths
# -------------------------------
DB_PATH: Final[str] = os.getenv("DB_PATH", os.path.join(".", "data", "sessions.db"))
TESSERACT_PATH: Final[str] = os.getenv(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe" if os.name == "nt" else "/usr/bin/tesseract"
)

# -------------------------------
# Path Validation & Setup
# -------------------------------
_db_dir = os.path.dirname(os.path.abspath(DB_PATH))
if not os.path.exists(_db_dir):
    try:
        os.makedirs(_db_dir, exist_ok=True)
        logger.info(f"Created missing database directory at {_db_dir}")
    except OSError as e:
        logger.error(f"Failed to create database directory at {_db_dir}: {e}")

if not os.path.isfile(TESSERACT_PATH):
    logger.warning(
        f"Tesseract executable not found at '{TESSERACT_PATH}'. "
        "Ensure it's installed and that the path is correctly set in the environment."
    )
