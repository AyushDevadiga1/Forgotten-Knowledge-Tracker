# config.py — FKT 2.0 — Single source of truth for all configuration
# config_manager.py is DEPRECATED. Do not import it anywhere.
# All settings live here or in the .env file at project root.
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (two levels up from this file: tracker_app/config.py)
_ENV_FILE = Path(__file__).parent.parent / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)
else:
    load_dotenv()  # fallback: search CWD

# ----------------------------
# Paths
# ----------------------------
PROJECT_ROOT = Path(__file__).parent.absolute()
DATA_DIR     = PROJECT_ROOT / "data"
MODELS_DIR   = PROJECT_ROOT / "models"
LOGS_DIR     = PROJECT_ROOT / "logs"

def setup_directories():
    """Create all required directories. Call once from main entry points."""
    for d in (DATA_DIR, MODELS_DIR, LOGS_DIR):
        d.mkdir(exist_ok=True)

# ----------------------------
# Database
# ----------------------------
DB_PATH = os.environ.get('FKT_TEST_DB', str(DATA_DIR / "sessions.db"))

# ----------------------------
# Tesseract OCR
# ----------------------------
def find_tesseract() -> str:
    """Locate Tesseract. Checks PATH, then common Windows install locations."""
    import shutil
    # 1. Honour explicit env override
    env_path = os.environ.get('TESSERACT_PATH', '')
    if env_path and os.path.exists(env_path):
        return env_path
    # 2. In system PATH
    if shutil.which("tesseract"):
        return "tesseract"
    # 3. Common Windows locations
    for p in [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\hp\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        str(Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe"),
    ]:
        if os.path.exists(p):
            return p
    # 4. Not found — setup.py will handle auto-download
    return r"C:\Program Files\Tesseract-OCR\tesseract.exe"

TESSERACT_PATH = find_tesseract()

# ----------------------------
# Tracking intervals (seconds)
# ----------------------------
TRACK_INTERVAL      = int(os.environ.get('TRACK_INTERVAL',      5))
SCREENSHOT_INTERVAL = int(os.environ.get('SCREENSHOT_INTERVAL', 20))
AUDIO_INTERVAL      = int(os.environ.get('AUDIO_INTERVAL',      15))
WEBCAM_INTERVAL     = int(os.environ.get('WEBCAM_INTERVAL',     45))
USER_ALLOW_WEBCAM   = os.environ.get('ALLOW_WEBCAM', 'true').lower() == 'true'

# ----------------------------
# Model paths
# ----------------------------
KNOWLEDGE_GRAPH_PATH = str(DATA_DIR / "knowledge_graph.pkl")

# ----------------------------
# Memory / SM-2 parameters
# ----------------------------
MEMORY_THRESHOLD         = 0.6
DEFAULT_LAMBDA           = 0.1
MIN_REVIEW_INTERVAL_HOURS = 1
MAX_REVIEW_INTERVAL_HOURS = 720

# ----------------------------
# Notifications
# ----------------------------
REMINDER_COOLDOWN_HOURS = 1
NOTIFICATION_TIMEOUT    = 10

# ----------------------------
# OCR
# ----------------------------
OCR_TOP_KEYWORDS          = 15
OCR_CONFIDENCE_THRESHOLD  = 0.3

# ----------------------------
# Audio
# ----------------------------
AUDIO_SAMPLE_RATE = 16000
AUDIO_DURATION    = 5

# ----------------------------
# Webcam
# ----------------------------
WEBCAM_FRAME_COUNT  = 5
WEBCAM_RESOLUTION   = (640, 480)

# ----------------------------
# Validation
# ----------------------------
def validate_config() -> list:
    """Return a list of configuration issue strings (empty = all good)."""
    import shutil
    issues = []

    if not DATA_DIR.exists():
        issues.append(f"Data directory missing: {DATA_DIR}")

    tess_in_path = TESSERACT_PATH.lower() == "tesseract"
    if tess_in_path and not shutil.which("tesseract"):
        issues.append("Tesseract not in PATH — run setup.py to auto-install")
    elif not tess_in_path and not os.path.exists(TESSERACT_PATH):
        issues.append(f"Tesseract not found at {TESSERACT_PATH} — run setup.py to auto-install")

    for val, name in [
        (TRACK_INTERVAL,      'TRACK_INTERVAL'),
        (SCREENSHOT_INTERVAL, 'SCREENSHOT_INTERVAL'),
        (AUDIO_INTERVAL,      'AUDIO_INTERVAL'),
        (WEBCAM_INTERVAL,     'WEBCAM_INTERVAL'),
    ]:
        if val <= 0:
            issues.append(f"{name} must be positive (got {val})")

    return issues


if __name__ == "__main__":
    setup_directories()
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Database     : {DB_PATH}")
    print(f"Tesseract    : {TESSERACT_PATH}")
    issues = validate_config()
    if issues:
        print("\nConfiguration issues:")
        for i in issues:
            print(f"  ! {i}")
    else:
        print("\nConfiguration OK.")