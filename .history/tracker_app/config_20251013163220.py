"""
config.py v3.1
---------------
Centralized configuration for Forgotten Knowledge Tracker (FKT) system.

Upgrades:
- Multi-modal history parameters (intent, attention, memory)
- Dynamic reload support
- Enhanced validation & fallback handling
- Versioning for module compatibility

IEEE Compliance:
- IEEE 1016 (Design Descriptions)
- IEEE 730 (Quality Assurance)
- IEEE 12207 (Configuration Management)
"""

import os
import logging
from typing import Final

# -------------------------------
# CONFIG VERSION
# -------------------------------
CONFIG_VERSION: Final[str] = "v3.1"

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
def _get_env_float(var_name: str, default: float, min_val: float = 0.0) -> float:
    raw_value = os.getenv(var_name, str(default))
    try:
        value = float(raw_value)
        if value < min_val:
            raise ValueError
        return value
    except (ValueError, TypeError):
        logger.warning(f"Invalid value for {var_name}='{raw_value}'. Using default: {default}")
        return default

def _get_env_bool(var_name: str, default: bool) -> bool:
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")

def _get_env_int(var_name: str, default: int, min_val: int = 0) -> int:
    raw_value = os.getenv(var_name, str(default))
    try:
        value = int(raw_value)
        if value < min_val:
            raise ValueError
        return value
    except (ValueError, TypeError):
        logger.warning(f"Invalid value for {var_name}='{raw_value}'. Using default: {default}")
        return default

# -------------------------------
# Tracker Intervals (seconds)
# -------------------------------
TRACK_INTERVAL: Final[float] = _get_env_float("TRACK_INTERVAL", 2.0, min_val=0.1)
SCREENSHOT_INTERVAL: Final[float] = _get_env_float("SCREENSHOT_INTERVAL", 10.0, min_val=1.0)
AUDIO_INTERVAL: Final[float] = _get_env_float("AUDIO_INTERVAL", 5.0, min_val=0.5)
WEBCAM_INTERVAL: Final[float] = _get_env_float("WEBCAM_INTERVAL", 30.0, min_val=5.0)

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
STALE_NODE_DAYS: Final[int] = _get_env_int("STALE_NODE_DAYS", 30, min_val=1)
FALLBACK_EMBEDDING_DIM: Final[int] = _get_env_int("FALLBACK_EMBEDDING_DIM", 384, min_val=16)

# -------------------------------
# Memory / Spacing Parameters
# -------------------------------
MEMORY_THRESHOLD: Final[float] = _get_env_float("MEMORY_THRESHOLD", 0.4)
MIN_LAMBDA: Final[float] = _get_env_float("MIN_LAMBDA", 0.05)
MAX_LAMBDA: Final[float] = _get_env_float("MAX_LAMBDA", 0.2)

# -------------------------------
# Intent Module Parameters
# -------------------------------
INTENT_CLASSIFIER_PATH: Final[str] = os.getenv("INTENT_CLASSIFIER_PATH", "core/intent_classifier.pkl")
INTENT_LABEL_MAP_PATH: Final[str] = os.getenv("INTENT_LABEL_MAP_PATH", "core/intent_label_map.pkl")
INTENT_HISTORY_LENGTH: Final[int] = _get_env_int("INTENT_HISTORY_LENGTH", 5, min_val=1)

# -------------------------------
# Multi-Modal History Parameters
# -------------------------------
ATTENTION_HISTORY_LENGTH: Final[int] = _get_env_int("ATTENTION_HISTORY_LENGTH", 5, min_val=1)
MEMORY_HISTORY_LENGTH: Final[int] = _get_env_int("MEMORY_HISTORY_LENGTH", 5, min_val=1)
INTERACTION_HISTORY_LENGTH: Final[int] = _get_env_int("INTERACTION_HISTORY_LENGTH", 5, min_val=1)

# -------------------------------
# Webcam Control
# -------------------------------
USER_ALLOW_WEBCAM: Final[bool] = _get_env_bool("USER_ALLOW_WEBCAM", False)

# -------------------------------
# Safety Checks
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

# -------------------------------
# Dynamic Reload Function
# -------------------------------
def reload_config():
    global TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL
    global MEMORY_THRESHOLD, MIN_LAMBDA, MAX_LAMBDA
    global INTENT_HISTORY_LENGTH, ATTENTION_HISTORY_LENGTH, MEMORY_HISTORY_LENGTH, INTERACTION_HISTORY_LENGTH
    global USER_ALLOW_WEBCAM
    TRACK_INTERVAL = _get_env_float("TRACK_INTERVAL", TRACK_INTERVAL)
    SCREENSHOT_INTERVAL = _get_env_float("SCREENSHOT_INTERVAL", SCREENSHOT_INTERVAL)
    AUDIO_INTERVAL = _get_env_float("AUDIO_INTERVAL", AUDIO_INTERVAL)
    WEBCAM_INTERVAL = _get_env_float("WEBCAM_INTERVAL", WEBCAM_INTERVAL)
    MEMORY_THRESHOLD = _get_env_float("MEMORY_THRESHOLD", MEMORY_THRESHOLD)
    MIN_LAMBDA = _get_env_float("MIN_LAMBDA", MIN_LAMBDA)
    MAX_LAMBDA = _get_env_float("MAX_LAMBDA", MAX_LAMBDA)
    INTENT_HISTORY_LENGTH = _get_env_int("INTENT_HISTORY_LENGTH", INTENT_HISTORY_LENGTH)
    ATTENTION_HISTORY_LENGTH = _get_env_int("ATTENTION_HISTORY_LENGTH", ATTENTION_HISTORY_LENGTH)
    MEMORY_HISTORY_LENGTH = _get_env_int("MEMORY_HISTORY_LENGTH", MEMORY_HISTORY_LENGTH)
    INTERACTION_HISTORY_LENGTH = _get_env_int("INTERACTION_HISTORY_LENGTH", INTERACTION_HISTORY_LENGTH)
    USER_ALLOW_WEBCAM = _get_env_bool("USER_ALLOW_WEBCAM", USER_ALLOW_WEBCAM)
    logger.info("Configuration reloaded from environment variables")
