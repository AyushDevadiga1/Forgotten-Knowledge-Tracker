"""
config.py
---------
Centralized configuration for Forgotten Knowledge Tracker (FKT) system.

IEEE-level upgrade: environment overrides, validation, and documentation.

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
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")

# -------------------------------
# Tracker Intervals (seconds)
# -------------------------------
TRACK_INTERVAL: Final[float] = _get_env_float("TRACK_INTERVAL", 2.0)
SCREENSHOT_INTERVAL: Final[float] = _get_env_float("SCREENSHOT_INTERVAL", 10.0)
AUDIO_INTERVAL: Final[float] = _get_env_float("AUDIO_INTERVAL", 5.0)
WEBCAM_INTERVAL: Final[float] = _get_env_float("WEBCAM_INTERVAL", 30.0)

# -------------------------------
# Database & Paths
# -------------------------------
DB_PATH: Final[str] = os.getenv("DB_PATH", os.path.join(".", "data", "sessions.db"))
GRAPH_PATH: Final[str] = os.getenv("GRAPH_PATH", "data/knowledge_graph.pkl")
TESSERACT_PATH: Final[str] = os.getenv(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe" if os.name == "nt" else "/usr/bin/tesseract"
)

# -------------------------------
# Knowledge Graph Parameters
# -------------------------------
GRAPH_SIMILARITY_THRESHOLD: Final[float] = _get_env_float("GRAPH_SIMILARITY_THRESHOLD", 0.75)
STALE_NODE_DAYS: Final[float] = _get_env_float("STALE_NODE_DAYS", 30)

# -------------------------------
# Memory / Spacing Parameters
# -------------------------------
MEMORY_THRESHOLD: Final[float] = _get_env_float("MEMORY_THRESHOLD", 0.4)
MIN_LAMBDA: Final[float] = _get_env_float("MIN_LAMBDA", 0.05)
MAX_LAMBDA: Final[float] = _get_env_float("MAX_LAMBDA", 0.2)
FALLBACK_EMBEDDING_DIM: Final[int] = int(_get_env_float("FALLBACK_EMBEDDING_DIM", 384))

# -------------------------------
# Intent Module Parameters
# -------------------------------
INTENT_CLASSIFIER_PATH: Final[str] = os.getenv("INTENT_CLASSIFIER_PATH", "core/intent_classifier.pkl")
INTENT_LABEL_MAP_PATH: Final[str] = os.getenv("INTENT_LABEL_MAP_PATH", "core/intent_label_map.pkl")
INTENT_HISTORY_LENGTH: Final[int] = int(_get_env_float("INTENT_HISTORY_LENGTH", 5))

# -------------------------------
# Webcam Control
# -------------------------------
USER_ALLOW_WEBCAM: Final[bool] = _get_env_bool("USER_ALLOW_WEBCAM", False)

# -------------------------------
# Validate & Create Paths
# -------------------------------
for path in [DB_PATH, os.path.dirname(GRAPH_PATH)]:
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
            logger.info(f"Created missing directory: {path}")
        except OSError as e:
            logger.error(f"Failed to create directory {path}: {e}")

if not os.path.isfile(TESSERACT_PATH):
    logger.warning(
        f"Tesseract executable not found at '{TESSERACT_PATH}'. "
        "Ensure it's installed and that the path is correctly set in the environment."
    )
