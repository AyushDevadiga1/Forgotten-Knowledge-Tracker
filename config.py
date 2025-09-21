# Global configuration for Forgotten Knowledge Tracker
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database path
DB_PATH = os.path.join(BASE_DIR, "db", "tracker.db")

# Sampling intervals (seconds)
WINDOW_POLL_INTERVAL = 3
SCREENSHOT_INTERVAL = 15
AUDIO_CLIP_DURATION = 5
VIDEO_FRAME_INTERVAL = 2
