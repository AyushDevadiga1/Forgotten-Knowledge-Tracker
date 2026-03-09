import time
import logging
from threading import Event, Lock
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
from pynput import keyboard, mouse

from tracker_app.config import TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL
from tracker_app.db.db_module import init_all_databases
from tracker_app.tracking.activity_monitor import ActivityMonitor
from tracker_app.tracking.intent_module import predict_intent

logger = logging.getLogger("TrackerLoop")

# Lazy-loaded modules
_ocr_pipeline = None
_audio_pipeline = None
_webcam_pipeline = None

def get_ocr_pipeline():
    global _ocr_pipeline
    if _ocr_pipeline is None:
        from tracker_app.tracking.ocr_module import ocr_pipeline
        _ocr_pipeline = ocr_pipeline
    return _ocr_pipeline

def get_audio_pipeline():
    global _audio_pipeline
    if _audio_pipeline is None:
        from tracker_app.tracking.audio_module import audio_pipeline
        _audio_pipeline = audio_pipeline
    return _audio_pipeline

def get_webcam_pipeline():
    global _webcam_pipeline
    if _webcam_pipeline is None:
        from tracker_app.tracking.webcam_module import webcam_pipeline
        _webcam_pipeline = webcam_pipeline
    return _webcam_pipeline

monitor = ActivityMonitor()

def on_key_press(key):
    monitor.keyboard_counter.increment()

def on_mouse_click(x, y, button, pressed):
    if pressed:
        monitor.mouse_counter.increment()

def start_listeners():
    try:
        kb_listener = keyboard.Listener(on_press=on_key_press)
        ms_listener = mouse.Listener(on_click=on_mouse_click)
        kb_listener.start()
        ms_listener.start()
        return kb_listener, ms_listener
    except Exception as e:
        logger.error(f"Error starting listeners: {e}")
        return None, None

def get_active_window() -> Tuple[str, float]:
    try:
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd) or "Unknown"
        except ImportError:
            title = "Unknown"  # Non-Windows platform
        total_events = monitor.keyboard_counter.get_value() + monitor.mouse_counter.get_value()
        interaction_rate = min(total_events / TRACK_INTERVAL if TRACK_INTERVAL > 0 else 0, 100)
        return title, interaction_rate
    except Exception as e:
        logger.error(f"Error getting active window: {e}")
        return "Unknown", 0

def track_loop(stop_event: Optional[Event] = None, webcam_enabled: bool = True):
    if stop_event is None:
        stop_event = Event()
    
    logger.info("Starting FKT tracking loop...")
    init_all_databases()
    kb_listener, ms_listener = start_listeners()
    
    if not kb_listener or not ms_listener:
        logger.error("Failed to start listeners")
        return
    
    monitor.start_session()
    
    audio_counter = ocr_counter = webcam_counter = save_counter = 0
    ocr_result = {'keywords': {}}
    audio_result = {'audio_label': 'silence'}
    
    try:
        while not stop_event.is_set():
            cycle_start = time.time()
            window_title, interaction_rate = get_active_window()
            
            # Audio
            audio_counter += TRACK_INTERVAL
            if audio_counter >= AUDIO_INTERVAL:
                try:
                    audio_pipeline = get_audio_pipeline()
                    audio_result = audio_pipeline()
                except Exception as e:
                    logger.warning(f"Audio processing error: {e}")
                audio_counter = 0
            
            # OCR
            ocr_counter += TRACK_INTERVAL
            if ocr_counter >= SCREENSHOT_INTERVAL:
                try:
                    ocr_pipeline = get_ocr_pipeline()
                    ocr_result = ocr_pipeline()
                    if ocr_result:
                        keywords = ocr_result.get('keywords', {})
                        monitor.process_concepts(keywords)
                except Exception as e:
                    logger.warning(f"OCR error: {e}")
                ocr_counter = 0
            
            # Webcam
            webcam_counter += TRACK_INTERVAL
            if webcam_counter >= WEBCAM_INTERVAL and webcam_enabled:
                try:
                    webcam_pipeline = get_webcam_pipeline()
                    webcam_result = webcam_pipeline()
                    monitor.update_attention(webcam_result.get('attentiveness_score', 0))
                except Exception as e:
                    logger.warning(f"Webcam error: {e}")
                webcam_counter = 0
            
            # Intent
            try:
                intent_result = predict_intent(
                    ocr_keywords=ocr_result.get('keywords', {}),
                    audio_label=audio_result.get('audio_label', 'silence'),
                    attention_score=monitor.session_attention_scores[-1] if monitor.session_attention_scores else 0,
                    interaction_rate=interaction_rate,
                    use_webcam=webcam_enabled
                )
                monitor.process_intent(intent_result, context=window_title)
            except Exception as e:
                logger.warning(f"Intent prediction error: {e}")
            
            # Periodic save
            save_counter += TRACK_INTERVAL
            if save_counter >= 300:
                monitor.export_tracking_data()
                save_counter = 0
            
            time.sleep(max(0.1, TRACK_INTERVAL - (time.time() - cycle_start)))
            
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        monitor.end_session()
        if kb_listener: kb_listener.stop()
        if ms_listener: ms_listener.stop()
        logger.info("Shutdown complete")

def ask_user_permissions():
    """Simple UI for permissions"""
    print("\n--- FKT Permissions ---")
    val = input("Enable webcam for attention tracking? (y/n): ")
    return val.lower().startswith('y')
