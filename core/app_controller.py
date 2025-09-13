import threading
import time
from datetime import datetime
from .tracker import TabTracker
from .screenshot import ScreenshotCapturer
from .ocr import OCRProcessor
from .database import DatabaseManager
from .audio import AudioMonitor, AudioProcessor
from .forgetting_curve import ForgettingCurve
from .reminder_system import ReminderSystem

class AppController:
    def __init__(self, screenshot_interval=30, audio_interval=300, db_path="data/tracking.db"):
        self.tracker = TabTracker(db_path=db_path)
        self.screenshot_capturer = ScreenshotCapturer()
        self.ocr_processor = OCRProcessor()
        self.db = DatabaseManager(db_path=db_path)
        self.screenshot_interval = screenshot_interval  # seconds
        self.audio_interval = audio_interval  # 5 minutes by default
        self.is_running = False
        self.screenshot_thread = None
        
        # Audio components
        self.audio_monitor = AudioMonitor()
        self.audio_processor = AudioProcessor()
        
        # Forgetting curve and reminder system
        self.forgetting_curve = ForgettingCurve()
        self.reminder_system = ReminderSystem(self.db, self.forgetting_curve)

    def start(self):
        """Start all tracking activities"""
        self.is_running = True
        self.tracker.start_tracking()
        self.start_screenshot_capture()
        self.start_audio_monitoring()
        
        # Start reminder system with daily checks
        self.reminder_system.start_daily_checks(['09:00', '14:00', '19:00'])
        
        print("✅ App controller started - tracking windows, screenshots, audio, and reminders")

    def start_screenshot_capture(self):
        """Start periodic screenshot capture in a separate thread"""
        def screenshot_loop():
            while self.is_running:
                time.sleep(self.screenshot_interval)
                self.capture_and_process_screenshot()

        self.screenshot_thread = threading.Thread(target=screenshot_loop)
        self.screenshot_thread.daemon = True
        self.screenshot_thread.start()

    def start_audio_monitoring(self):
        """Start audio monitoring with database integration"""
        self.audio_monitor.start_continuous_monitoring(
            interval=self.audio_interval,
            db_manager=self.db,
            audio_processor=self.audio_processor
        )
        print("🎤 Audio monitoring started with database integration")

    def stop_audio_monitoring(self):
        """Stop audio monitoring"""
        self.audio_monitor.stop_monitoring()
        print("🎤 Audio monitoring stopped")

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

    def process_audio_file(self, audio_path):
        """Process an audio file (transcribe and analyze)"""
        try:
            # Transcribe audio
            transcription = self.audio_processor.transcribe_audio(audio_path)
            
            if transcription['success']:
                # Analyze content
                analysis = self.audio_processor.analyze_audio_content(transcription['text'])
                
                # Save to database
                self.db.save_audio_recording(
                    file_path=audio_path,
                    timestamp=datetime.now().isoformat(),
                    duration=30,  # Assuming 30-second recordings
                    transcribed_text=transcription['text'],
                    confidence=transcription['confidence'],
                    word_count=transcription['word_count'],
                    keywords=analysis['keywords'],
                    is_educational=analysis['is_educational']
                )
                
                print(f"🎵 Processed audio: {len(transcription['text'])} characters")
                
        except Exception as e:
            print(f"❌ Error processing audio: {e}")

    def stop(self):
        """Stop all tracking activities"""
        self.is_running = False
        self.tracker.stop_tracking()
        self.stop_audio_monitoring()
        self.reminder_system.stop()  # Stop reminder system
        
        if self.screenshot_thread:
            self.screenshot_thread.join(timeout=2.0)
        print("🛑 App controller stopped")

    def get_stats(self):
        """Get comprehensive statistics"""
        audio_stats = self.db.get_audio_stats()
        
        # Get reminder stats if available
        reminder_stats = {}
        if hasattr(self.reminder_system, 'get_stats'):
            reminder_stats = self.reminder_system.get_stats()
        
        return {
            "window_stats": self.tracker.get_stats(),
            "screenshot_count": self.db.get_screenshot_count(),
            "ocr_processing_count": self.db.get_ocr_result_count(),
            "audio_stats": audio_stats,
            "reminder_stats": reminder_stats
        }

    def trigger_manual_review_check(self):
        """Manually trigger a review check (for testing)"""
        print("🔍 Manually triggering review check...")
        self.reminder_system.check_for_reviews()