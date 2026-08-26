"""Shared magic-number constants for the tracker app.

All tunable thresholds, limits, and defaults live here.
Import from here instead of hardcoding in individual modules.
"""

# ---------------------------------------------------------------------------
# Attention / scoring defaults
# ---------------------------------------------------------------------------
NEUTRAL_ATTENTION = 50.0          # Default when no signal is available
ATTENTION_WEIGHT_WEBCAM = 0.70    # Webcam share in blended attention score
ATTENTION_WEIGHT_CLE = 0.30       # CLE share in blended attention score

# ---------------------------------------------------------------------------
# Mastery thresholds
# ---------------------------------------------------------------------------
MASTERY_SUCCESS_RATE = 0.95       # Required correct/total ratio
MASTERY_MIN_REPETITIONS = 5       # Minimum reviews before mastery

# ---------------------------------------------------------------------------
# Question / text limits
# ---------------------------------------------------------------------------
QUESTION_MAX_LENGTH = 1000        # Max characters for a quiz question
TEXT_MIN_LENGTH = 10              # Minimum meaningful text length
TEXT_TOP_KEYWORDS = 15            # Default top_n for keyword extraction

# ---------------------------------------------------------------------------
# API limits
# ---------------------------------------------------------------------------
GRAPH_GAPS_MAX_LIMIT = 50         # Max limit for /graph/gaps endpoint
GRAPH_GAPS_MAX_DAYS = 90          # Max days for trend window
BROWSER_INGEST_MAX_TEXT = 10000   # Max raw text from browser ingest
BROWSER_INGEST_MIN_TEXT = 20      # Min text length for browser ingest
TITLE_MAX_LENGTH = 200            # Truncation limit for browser titles
CONTEXT_MAX_LENGTH = 80           # Truncation limit for context snippets
CONTEXT_SNIPPET_MAX = 200         # Truncation limit for scheduler context

# ---------------------------------------------------------------------------
# Pipeline / threading
# ---------------------------------------------------------------------------
PIPELINE_MAX_WORKERS = 3          # ThreadPoolExecutor worker count
PIPELINE_FUTURE_TIMEOUT = 8       # Seconds to wait for a pipeline future
PERIODIC_EXPORT_INTERVAL = 300    # Seconds between periodic JSON exports

# ---------------------------------------------------------------------------
# Retraining
# ---------------------------------------------------------------------------
RETRAIN_EVERY_N = 50              # Retrain after every N corrections
RETRAIN_TIMEOUT = 180             # Seconds before killing retrain subprocess
RETRAIN_TEST_SIZE = 0.20          # Train/test split ratio
RETRAIN_MIN_SPLITS = 5            # Minimum cross-validation folds
RETRAIN_N_ESTIMATORS = 200        # RandomForest tree count
RETRAIN_MAX_DEPTH = 12            # RandomForest max depth
RETRAIN_MIN_SAMPLES_LEAF = 3      # RandomForest leaf size

# ---------------------------------------------------------------------------
# CPU throttling
# ---------------------------------------------------------------------------
CPU_HIGH_THRESHOLD = 70           # % CPU above which to throttle hard
CPU_MID_THRESHOLD = 50            # % CPU above which to throttle mildly
CPU_THROTTLE_HIGH = 2.5           # Sleep multiplier when CPU is high
CPU_THROTTLE_MID = 1.5            # Sleep multiplier when CPU is moderate
CPU_THROTTLE_LOW = 1.0            # Sleep multiplier when CPU is low

# ---------------------------------------------------------------------------
# SM-2 quality scale
# ---------------------------------------------------------------------------
SM2_MIN_QUALITY = 0
SM2_MAX_QUALITY = 5

# ---------------------------------------------------------------------------
# Lock / file timeouts
# ---------------------------------------------------------------------------
FILE_LOCK_TIMEOUT = 5             # Seconds to wait for session file lock

# ---------------------------------------------------------------------------
# Web defaults
# ---------------------------------------------------------------------------
DEFAULT_PORT = 5000               # Flask dev server port
DEFAULT_REVIEW_LIMIT = 20         # Default item limit for due-items query
DEFAULT_ITEMS_LIMIT = 50          # Default item limit for general queries
DEFAULT_CONCEPT_LIMIT = 50        # Default concept limit for graph queries
DEFAULT_HISTORY_DAYS = 30         # Default history window in days
DEFAULT_CONCEPT_SCHEDULER_LIMIT = 10  # Default due-concepts limit

# ---------------------------------------------------------------------------
# Knowledge graph eviction
# ---------------------------------------------------------------------------
DEFAULT_MEMORY_SCORE = 0.5        # Eviction priority when no score exists

# ---------------------------------------------------------------------------
# Activity monitor
# ---------------------------------------------------------------------------
ACTIVITY_BUFFER_SIZE = 100        # Prediction ring-buffer length

# ---------------------------------------------------------------------------
# Webcam calibration
# ---------------------------------------------------------------------------
EAR_CALIBRATION_SIGMA_LOW = 1.5  # Std-devs below mean for personal low
EAR_CALIBRATION_SIGMA_HIGH = 1.0 # Std-devs above mean for personal high
EAR_ABSOLUTE_LOW = 0.05           # Minimum plausible EAR
EAR_ABSOLUTE_HIGH = 0.50          # Maximum plausible EAR
EAR_ATTENTIVENESS_FLOOR = 40.0   # Min attentiveness from EAR
EAR_ATTENTIVENESS_RANGE = 60.0   # Max attentiveness range from EAR
CAMERA_RETRY_DELAY = 0.5         # Seconds between camera retries
CAMERA_CALIBRATION_DELAY = 0.1   # Seconds between calibration samples

# ---------------------------------------------------------------------------
# YAKE keyword extraction
# ---------------------------------------------------------------------------
YAKE_NGRAM_SIZE = 2
YAKE_DEDUPLICATION_LIMIT = 0.7
YAKE_WINDOW_SIZE = 2
YAKE_TOP_KEYWORDS = 20

# ---------------------------------------------------------------------------
# Audio module
# ---------------------------------------------------------------------------
AUDIO_MUSIC_ZCR_THRESHOLD = 0.15
AUDIO_MUSIC_SC_THRESHOLD = 2500
AUDIO_MUSIC_CONFIDENCE = 0.60
AUDIO_N_MFCC = 13
AUDIO_HOP_LENGTH = 256

# ---------------------------------------------------------------------------
# CLE module
# ---------------------------------------------------------------------------
CLE_IKI_CEILING_MS = 5000        # Max inter-keystroke interval to consider
CLE_PAUSE_TARGET_DENSITY = 0.3   # Ideal pause density for scoring
CLE_PAUSE_MAX_DENSITY = 0.6      # Density above which pause score = 0
CLE_BAND_LOW = 0.15
CLE_BAND_MID_LOW = 0.35
CLE_BAND_MID_HIGH = 0.55
CLE_BAND_HIGH = 0.75
