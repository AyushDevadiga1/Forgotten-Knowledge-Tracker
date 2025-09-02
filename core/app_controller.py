import threading
import time
from datetime import datetime
from .tracker import TabTracker
from .screenshot import ScreenshotCapturer
from .ocr import OCRProcessor
from .database import DatabaseManager

class AppController:
    def __init__(self, screenshot_interval=30, db_path="data/tracking.db"):
        self.tracker = TabTracker(db_path=db_path)
        self.screenshot_capturer = ScreenshotCapturer()
        self.ocr_processor = OCRProcessor()
        self.db = DatabaseManager(db_path=db_path)
        self.screenshot_interval = screenshot_interval  # seconds
        self.is_running = False
        self.screenshot_thread = None
    
    def start(self):
        """Start both window tracking and periodic screenshot capture"""
        self.is_running = True
        self.tracker.start_tracking()
        self.start_screenshot_capture()
        print("✅ App controller started - tracking windows and capturing screenshots")
    
    def start_screenshot_capture(self):
        """Start periodic screenshot capture in a separate thread"""
        def screenshot_loop():
            while self.is_running:
                time.sleep(self.screenshot_interval)
                self.capture_and_process_screenshot()
        
        self.screenshot_thread = threading.Thread(target=screenshot_loop)
        self.screenshot_thread.daemon = True
        self.screenshot_thread.start()
    
    def capture_and_process_screenshot(self):
        """Capture screenshot, extract text, and save to database"""
        try:
            # Get current window info - use a safer approach
            current_window = {}
            try:
                # Try to get window info from the tracker's current data
                if hasattr(self.tracker, 'current_window') and self.tracker.current_window:
                    current_window = self.tracker.current_window
                elif hasattr(self.tracker, 'get_current_window_info'):
                    current_window = self.tracker.get_current_window_info()
            except Exception as e:
                print(f"⚠️  Could not get window info: {e}")
                current_window = {'title': 'Unknown', 'app': 'Unknown'}
            
            # Capture screenshot
            screenshot = self.screenshot_capturer.capture_screenshot()
            
            # Extract text via OCR
            ocr_result = self.ocr_processor.extract_text_from_image(screenshot['path'])
            
            # Save to database
            screenshot_id = self.db.save_screenshot(
                screenshot['path'], 
                datetime.now().isoformat(),
                current_window.get('title', 'Unknown'),
                current_window.get('app', 'Unknown')
            )
            
            if screenshot_id:
                self.db.save_ocr_result(
                    screenshot_id,
                    ocr_result['text'],
                    ocr_result.get('confidence', 0.0),
                    ocr_result.get('word_count', 0)
                )
                
                print(f"📸 Captured and processed screenshot #{screenshot_id}")
            else:
                print("❌ Failed to save screenshot to database")
                
        except Exception as e:
            print(f"❌ Error in screenshot capture: {e}")
    
    def stop(self):
        """Stop all tracking activities"""
        self.is_running = False
        self.tracker.stop_tracking()
        if self.screenshot_thread:
            self.screenshot_thread.join(timeout=2.0)
        print("🛑 App controller stopped")
    
    def get_stats(self):
        """Get comprehensive statistics"""
        return {
            "window_stats": self.tracker.get_stats(),
            "screenshot_count": self.db.get_screenshot_count(),
            "ocr_processing_count": self.db.get_ocr_result_count()
        }