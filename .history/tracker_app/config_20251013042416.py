"""
config.py
---------
Centralized configuration file for the Forgotten Knowledge Tracker (FKT) system.

IEEE-Level Design (Compliant with):
- IEEE 1016: Software Design Descriptions
- IEEE 730: Quality Assurance Plan
- IEEE 12207: Configuration Management

Provides:
- Safe environment overrides
- Centralized path management
- Runtime validation and logging
- Modular constants for all core sensory systems
"""

import os
import logging
from typing import Final, Optional

# ============================================================
# LOGGER SETUP
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/config_init.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Config")

# ============================================================
# ENV HELPERS
# ============================================================
def _get_env_float(var_name: str, default: float) -> float:
    """Fetch a float environment variable safely with positive constraint."""
    raw = os.getenv(var_name, str(default))
    try:
        value = float(raw)
        if value <= 0:
            raise ValueError
        return value
    except (ValueError, TypeError):
        logger.warning(f"[Config] Invalid or non-positive float for {var_name}='{raw}', using default={default}")
        return default


def _get_env_int(var_name: str, default: int) -> int:
    """Fetch an integer environment variable safely."""
    raw = os.getenv(var_name, str(default))
    try:
        value = int(raw)
        return value
    except (ValueError, TypeError):
        logger.warning(f"[Config] Invalid integer for {var_name}='{raw}', using default={default}")
        return default


def _get_env_bool(var_name: str, default: bool) -> bool:
    """Fetch a boolean environment variable."""
    raw = os.getenv(var_name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _get_env_path(var_name: str, default: str) -> str:
    """Resolve a file or directory path safely."""
    path = os.getenv(var_name, default)
    return os.path.normpath(os.path.expanduser(path))

# ============================================================
# CORE TIMING CONSTANTS (seconds)
# ============================================================
TRACK_INTERVAL: Final[float] = _get_env_float("TRACK_INTERVAL", 2.0)
SCREENSHOT_INTERVAL: Final[float] = _get_env_float("SCREENSHOT_INTERVAL", 10.0)
AUDIO_INTERVAL: Final[float] = _get_env_float("AUDIO_INTERVAL", 5.0)
WEBCAM_INTERVAL: Final[float] = _get_env_float("WEBCAM_INTERVAL", 30.0)
REMINDER_CHECK_INTERVAL: Final[int] = _get_env_int("REMINDER_CHECK_INTERVAL", 60)

# ============================================================
# DATABASE AND GRAPH PATHS
# ============================================================
DB_PATH: Final[str] = _get_env_path("DB_PATH", os.path.join(".", "data", "sessions.db"))
GRAPH_PATH: Final[str] = _get_env_path("GRAPH_PATH", os.path.join(".", "data", "knowledge_graph.pkl"))
BACKUP_DIR: Final[str] = _get_env_path("BACKUP_DIR", os.path.join(".", "backups"))

# ============================================================
# OCR CONFIGURATION
# ============================================================
TESSERACT_PATH: Final[str] = _get_env_path(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe" if os.name == "nt" else "/usr/bin/tesseract"
)
OCR_LANG: Final[str] = os.getenv("OCR_LANG", "eng")
OCR_CACHE_SIZE: Final[int] = _get_env_int("OCR_CACHE_SIZE", 200)

# ============================================================
# AUDIO CONFIGURATION
# ============================================================
AUDIO_SAMPLE_RATE: Final[int] = _get_env_int("AUDIO_SAMPLE_RATE", 16000)
AUDIO_BUFFER_SECONDS: Final[int] = _get_env_int("AUDIO_BUFFER_SECONDS", 3)
AUDIO_CONF_THRESHOLD: Final[float] = _get_env_float("AUDIO_CONF_THRESHOLD", 0.65)

# ============================================================
# WEBCAM CONFIGURATION
# ============================================================
USER_ALLOW_WEBCAM: Final[bool] = _get_env_bool("USER_ALLOW_WEBCAM", False)
CAMERA_INDEX: Final[int] = _get_env_int("CAMERA_INDEX", 0)
FACE_DETECT_CONF_THRESHOLD: Final[float] = _get_env_float("FACE_DETECT_CONF_THRESHOLD", 0.7)

# ============================================================
# MEMORY MODEL & DECAY SETTINGS
# ============================================================
MEMORY_DECAY_RATE: Final[float] = _get_env_float("MEMORY_DECAY_RATE", 0.1)
RECALL_THRESHOLD: Final[float] = _get_env_float("RECALL_THRESHOLD", 0.5)
MAX_MEMORY_SAMPLES: Final[int] = _get_env_int("MAX_MEMORY_SAMPLES", 500)

# ============================================================
# SAFETY & ENVIRONMENT VALIDATION
# ============================================================
def validate_environment() -> None:
    """Perform runtime validation of core paths and executables."""
    # Create directories if missing
    for d in ["logs", os.path.dirname(DB_PATH), BACKUP_DIR]:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directory {d}: {e}")

    # Warn for missing Tesseract
    if not os.path.isfile(TESSERACT_PATH):
        logger.warning(f"Tesseract not found at '{TESSERACT_PATH}'. OCR may be disabled.")

    # Confirm DB accessibility
    try:
        db_dir = os.path.dirname(DB_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        open(DB_PATH, "a").close()
        logger.info(f"Database path validated: {DB_PATH}")
    except Exception as e:
        logger.error(f"Database validation failed: {e}")

# ============================================================
# EXECUTION GUARD
# ============================================================
if __name__ == "__main__":
    logger.info("Running FKT config validation...")
    validate_environment()
    logger.info("✅ Configuration initialized successfully.")
