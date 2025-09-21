# Phase 2: screenshots
import time
from PIL import ImageGrab
from config import SCREENSHOT_INTERVAL

def capture_screenshot():
    # Capture the whole screen (or customize bounding box)
    screenshot = ImageGrab.grab()
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    file_path = f"screenshots/screen_{timestamp}.png"
    screenshot.save(file_path)
    return file_path
