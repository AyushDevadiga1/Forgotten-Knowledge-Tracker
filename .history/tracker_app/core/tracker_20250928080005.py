# tracker.py - FIXED VERSION
import time
import sqlite3
import logging
from datetime import datetime, timedelta
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

# Import config first
from config import DB_PATH, ENHANCED_DB_PATH, TRACK_INTERVAL, SCREENSHOT_INTERVAL
from config import AUDIO_INTERVAL, WEBCAM_INTERVAL, RETENTION_DAYS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fkt_tracker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import win32gui
    from pynput import keyboard, mouse
    from plyer import notification
    
    # Import our modules
    from db_module import init_db, init_enhanced_db, log_session, log_enhanced_session
    from db_module import log_concept_memory_prediction, update_enhanced_concept
    from db_module import delete_old_enhanced_data, save_user_preferences, load_user_preferences
    from db_module import initialize_all_databases
    
    from ocr_module import enhanced_ocr_pipeline
    from audio_module import enhanced_audio_pipeline
    from webcam_module import enhanced_webcam_pipeline
    from intent_module import predict_intent_enhanced
    from knowledge_graph import add_concepts_enhanced, get_graph
    from memory_model import compute_memory_score_enhanced
    from face_detection_module import FaceDetector
    
    IMPORT_SUCCESS = True
except ImportError as e:
    logger.error(f"Import error: {e}")
    IMPORT_SUCCESS = False

class KnowledgeTracker:
    def __init__(self):
        self.keyboard_events = 0
        self.mouse_events = 0
        self.kb_listener = None
        self.ms_listener = None
        self.face_detector = None
        
        # State tracking
        self.latest_ocr = {"keywords": [], "confidence": 0.0, "raw_text": ""}
        self.latest_audio = {"audio_label": "silence", "confidence": 0.0}
        self.latest_attention = 0
        self.latest_interaction = 0
        self.latest_app_type = "unknown"
        self.latest_window_title = "Unknown"
        
        # Counters
        self.ocr_counter = 0
        self.audio_counter = 0
        self.webcam_counter = 0
        self.retention_counter = 0
        
        # Configuration
        self.preferences = {}
        self.use_enhanced = True

    def get_active_window(self):
        """Get active window information"""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            
            # Simple app classification
            title_lower = title.lower()
            if any(app in title_lower for app in ["chrome", "firefox", "edge", "browser"]):
                app_type = "browser"
            elif any(app in title_lower for app in ["word", "pdf", "notepad"]):
                app_type = "document"
            elif any(app in title_lower for app in ["vscode", "pycharm", "visual studio"]):
                app_type = "ide"
            else:
                app_type = "unknown"
                
            return title, app_type, self.keyboard_events + self.mouse_events
        except Exception as e:
            logger.error(f"Window detection error: {e}")
            return "Unknown", "unknown", 0

    def on_key_press(self, key):
        """Keyboard event handler"""
        self.keyboard_events += 1
        
    def on_mouse_click(self, x, y, button, pressed):
        """Mouse event handler"""
        if pressed:
            self.mouse_events += 1

    def initialize(self):
        """Initialize the tracker system"""
        if not IMPORT_SUCCESS:
            raise RuntimeError("Required modules not available")
        
        # Initialize databases
        try:
            initialize_all_databases()
            logger.info("Databases initialized")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
        
        # Start input listeners
        try:
            self.kb_listener = keyboard.Listener(on_press=self.on_key_press)
            self.ms_listener = mouse.Listener(on_click=self.on_mouse_click)
            self.kb_listener.start()
            self.ms_listener.start()
            logger.info("Input listeners started")
        except Exception as e:
            logger.error(f"Listener start error: {e}")
        
        # Load user preferences
        try:
            self.preferences = load_user_preferences()
            self.use_enhanced = self.preferences.get('novel_algorithms_enabled', True)
            logger.info(f"Preferences loaded - Enhanced mode: {self.use_enhanced}")
        except Exception as e:
            logger.error(f"Preferences load error: {e}")
            self.preferences = {
                'ocr_enabled': True,
                'audio_enabled': False,
                'webcam_enabled': False,
                'novel_algorithms_enabled': True
            }

    def run_tracking_cycle(self):
        """Execute one complete tracking cycle"""
        try:
            # Update counters
            self.ocr_counter += TRACK_INTERVAL
            self.audio_counter += TRACK_INTERVAL
            self.webcam_counter += TRACK_INTERVAL
            
            # Get active window information
            window_title, app_type, interaction_rate = self.get_active_window()
            self.latest_window_title = window_title
            self.latest_app_type = app_type
            self.latest_interaction = interaction_rate
            
            # Log to original database
            try:
                log_session(window_title, interaction_rate)
            except Exception as e:
                logger.error(f"Session log error: {e}")
            
            # Enhanced logging
            session_id = None
            if self.use_enhanced:
                try:
                    session_id = log_enhanced_session(
                        window_title=window_title,
                        app_type=app_type,
                        interaction_rate=interaction_rate,
                        ocr_data=self.latest_ocr,
                        audio_data=self.latest_audio,
                        attention_score=self.latest_attention,
                        algorithm_version="enhanced_v1"
                    )
                except Exception as e:
                    logger.error(f"Enhanced session log error: {e}")
            
            # Process OCR if enabled
            if self.preferences.get('ocr_enabled', True) and self.ocr_counter >= SCREENSHOT_INTERVAL:
                try:
                    ocr_data = enhanced_ocr_pipeline()
                    self.latest_ocr = ocr_data
                    self.ocr_counter = 0
                    
                    # Add concepts to knowledge graph
                    if ocr_data.get('keywords'):
                        try:
                            add_concepts_enhanced(
                                concepts=ocr_data['keywords'],
                                ocr_confidence=ocr_data.get('confidence', 0.5),
                                audio_confidence=self.latest_audio.get('confidence', 0.5),
                                attention_score=self.latest_attention,
                                interaction_rate=interaction_rate,
                                app_type=app_type
                            )
                        except Exception as e:
                            logger.error(f"Concept addition error: {e}")
                except Exception as e:
                    logger.error(f"OCR processing error: {e}")
            
            # Process audio if enabled
            if self.preferences.get('audio_enabled', False) and self.audio_counter >= AUDIO_INTERVAL:
                try:
                    audio_data = enhanced_audio_pipeline()
                    self.latest_audio = audio_data
                    self.audio_counter = 0
                except Exception as e:
                    logger.error(f"Audio processing error: {e}")
            
            # Process webcam if enabled
            if self.preferences.get('webcam_enabled', False) and self.webcam_counter >= WEBCAM_INTERVAL:
                try:
                    webcam_data = enhanced_webcam_pipeline()
                    self.latest_attention = webcam_data.get('attentiveness_score', 0)
                    self.webcam_counter = 0
                except Exception as e:
                    logger.error(f"Webcam processing error: {e}")
            
            # Predict user intent
            try:
                intent_data = predict_intent_enhanced(
                    ocr_keywords=self.latest_ocr.get('keywords', []),
                    audio_data=self.latest_audio,
                    attention_data={"attentiveness_score": self.latest_attention},
                    interaction_rate=interaction_rate,
                    app_type=app_type,
                    use_webcam=self.preferences.get('webcam_enabled', False),
                    ocr_confidence=self.latest_ocr.get('confidence', 0.5)
                )
            except Exception as e:
                logger.error(f"Intent prediction error: {e}")
                intent_data = {"intent_label": "unknown", "confidence": 0.0}
            
            # Log completion
            logger.info(
                f"Cycle | Window: {window_title[:20]}... | "
                f"Intent: {intent_data.get('intent_label', 'unknown')} | "
                f"Interactions: {interaction_rate}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Tracking cycle error: {e}")
            return False

    def run(self):
        """Main tracking loop"""
        if not IMPORT_SUCCESS:
            logger.error("Cannot start tracker - missing dependencies")
            return
            
        try:
            self.initialize()
            logger.info("Knowledge tracker started successfully")
            
            while True:
                success = self.run_tracking_cycle()
                if not success:
                    logger.warning("Tracking cycle failed")
                
                time.sleep(TRACK_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("Tracker stopped by user")
        except Exception as e:
            logger.error(f"Tracker fatal error: {e}")
        finally:
            if self.kb_listener:
                self.kb_listener.stop()
            if self.ms_listener:
                self.ms_listener.stop()
            logger.info("Tracker shutdown complete")

def ask_user_permissions():
    """Interactive permission setup"""
    print("="*60)
    print("           KNOWLEDGE TRACKER - IEEE EDITION")
    print("="*60)
    
    responses = {}
    
    responses['enhanced'] = input("Use enhanced AI algorithms? (y/n, default=y): ").lower().strip() != 'n'
    responses['ocr'] = input("Enable OCR/text tracking? (y/n, default=y): ").lower().strip() != 'n'
    responses['audio'] = input("Enable audio context tracking? (y/n, default=n): ").lower().strip() == 'y'
    responses['webcam'] = input("Enable webcam attention tracking? (y/n, default=n): ").lower().strip() == 'y'
    
    retention_input = input("Data retention days (default=30): ").strip()
    responses['retention'] = int(retention_input) if retention_input.isdigit() else 30
    
    print("\n" + "="*60)
    consent = input("Start tracking with these settings? (y/n): ").lower() == 'y'
    
    if consent:
        try:
            save_user_preferences(
                ocr_enabled=responses['ocr'],
                audio_enabled=responses['audio'],
                webcam_enabled=responses['webcam'],
                novel_algorithms_enabled=responses['enhanced'],
                data_retention_days=responses['retention'],
                consent_given=True
            )
            return True
        except Exception as e:
            print(f"Error saving preferences: {e}")
            return False
    else:
        print("Tracker setup cancelled.")
        return False

if __name__ == "__main__":
    print("Forgotten Knowledge Tracker - IEEE Edition")
    
    if ask_user_permissions():
        tracker = KnowledgeTracker()
        tracker.run()
    else:
        print("Tracker exited.")