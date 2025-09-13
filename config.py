import os

# Database configuration
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'tracking.db')

# Web interface configuration
WEB_HOST = '0.0.0.0'
WEB_PORT = 5000
DEBUG = True

# Tracking intervals
SCREENSHOT_INTERVAL = 30
AUDIO_INTERVAL = 300