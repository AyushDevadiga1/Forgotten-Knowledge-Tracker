"""Single source of truth for FKT configuration (env- and .env-driven).

tracker_app.config_manager is DEPRECATED — never import it.
"""
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
def get_db_path() -> str:
    """Resolve the SQLite DB path at call time.

    Reads FKT_TEST_DB from the environment on every call (falling back to
    DATA_DIR / "sessions.db"), so a value set AFTER this module was imported
    is still honored by callers. DB_PATH below stays frozen at import time
    for backward compatibility.
    """
    return os.environ.get('FKT_TEST_DB', str(DATA_DIR / "sessions.db"))

DB_PATH = get_db_path()

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
# Study-session capture
# ----------------------------
# Intent labels allowed to persist concepts inside an active study session.
# Default: only 'studying'. Re-enable passive reading capture with:
#   SESSION_ALLOWED_INTENTS=studying,passive
SESSION_ALLOWED_INTENTS = tuple(
    x.strip()
    for x in os.environ.get('SESSION_ALLOWED_INTENTS', 'studying').split(',')
    if x.strip()
)

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

# Min gap (minutes) between intent-feedback toast prompts. The tracker writes a
# new intent_predictions row every ~5 s, so without this the toast would nag
# almost constantly. Tune with INTENT_TOAST_COOLDOWN_MINUTES.
TOAST_COOLDOWN_MINUTES = int(os.environ.get('INTENT_TOAST_COOLDOWN_MINUTES', 5))

# ----------------------------
# OCR
# ----------------------------
OCR_TOP_KEYWORDS          = 15
# Per-word Tesseract confidence floor (0-100). Words below this are dropped
# before keyword extraction: OCR misreads of UI chrome / overlapping windows
# typically score ~0 while readable study content scores 50-95, so this keeps
# junk out of tracked_concepts at the source. Tunable via OCR_MIN_WORD_CONFIDENCE.
OCR_MIN_WORD_CONFIDENCE   = int(os.environ.get('OCR_MIN_WORD_CONFIDENCE', 30))

# ----------------------------
# EAR Calibration
# ----------------------------
CALIBRATION_DURATION_SECONDS = int(os.environ.get('CALIBRATION_DURATION_SECONDS', 30))
CALIBRATION_MIN_SAMPLES = int(os.environ.get('CALIBRATION_MIN_SAMPLES', 20))

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