"""
Enhanced Activity Tracker with Intelligent Concept Scheduling

Improves the original tracker.py with:
- SM-2 scheduling for encountered concepts
- Intent prediction validation & learning
- Tracking analytics
- Graceful error recovery
- Dashboard integration
- Data export capabilities
"""

import time
import sqlite3
import json
import pickle
import os
import threading
from threading import Event, Lock
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict
import logging

import cv2
import numpy as np
from pynput import keyboard, mouse
import win32gui

from tracker_app.core.db_module import init_all_databases, get_db_connection
from tracker_app.config import DB_PATH, TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL, validate_config, DATA_DIR
from tracker_app.core.intent_module import predict_intent
from tracker_app.core.knowledge_graph import add_concepts, get_graph, add_edges

# Configure logging FIRST — must be before any function that calls logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Tracker")

# Lazy-loaded modules (loaded on first use to optimize startup time)
_ocr_pipeline = None
_audio_pipeline = None
_webcam_pipeline = None

def get_ocr_pipeline():
    """Lazy load OCR pipeline"""
    global _ocr_pipeline
    if _ocr_pipeline is None:
        logger.info("Loading OCR pipeline...")
        from tracker_app.core.ocr_module import ocr_pipeline
        _ocr_pipeline = ocr_pipeline
    return _ocr_pipeline

def get_audio_pipeline():
    """Lazy load audio pipeline"""
    global _audio_pipeline
    if _audio_pipeline is None:
        logger.info("Loading audio pipeline...")
        from tracker_app.core.audio_module import audio_pipeline
        _audio_pipeline = audio_pipeline
    return _audio_pipeline

def get_webcam_pipeline():
    """Lazy load webcam pipeline"""
    global _webcam_pipeline
    if _webcam_pipeline is None:
        logger.info("Loading webcam pipeline...")
        from tracker_app.core.webcam_module import webcam_pipeline
        _webcam_pipeline = webcam_pipeline
    return _webcam_pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Tracker")


from tracker_app.core.concept_scheduler import ConceptScheduler
from tracker_app.core.activity_monitor import ActivityMonitor, ThreadSafeCounter

# Global tracker instance
tracker_instance = ActivityMonitor()


def on_key_press(key):
    """Keyboard event handler"""
    tracker_instance.keyboard_counter.increment()


def on_mouse_click(x, y, button, pressed):
    """Mouse event handler"""
    if pressed:
        tracker_instance.mouse_counter.increment()


def start_listeners():
    """Start input listeners"""
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
    """Get active window and interaction rate"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or "Unknown"
        
        total_events = tracker_instance.keyboard_counter.get_value() + tracker_instance.mouse_counter.get_value()
        interaction_rate = min(total_events / TRACK_INTERVAL if TRACK_INTERVAL > 0 else 0, 100)
        
        return title, interaction_rate
    except Exception as e:
        logger.error(f"Error getting active window: {e}")
        return "Unknown", 0

def ask_user_permissions() -> bool:
    """Explicitly ask for webcam permissions"""
    try:
        print("\\n=== Privacy Control ===")
        choice = input("Enable facial attention tracking (webcam)? (y/n): ").lower().strip()
        allow_webcam = choice in ['y', 'yes', 'e']
        print(f"Webcam Tracking: {'ENABLED' if allow_webcam else 'DISABLED'}")
        
        if allow_webcam:
            print("Note: All data is processed locally. No images are uploaded.")
            
        return allow_webcam
    except Exception:
        return False

def track_loop(stop_event: Optional[Event] = None, webcam_enabled: bool = True):
    """Enhanced tracking loop with all improvements"""
    if stop_event is None:
        stop_event = Event()
    
    logger.info("Starting enhanced tracking loop...")
    
    # Validate configuration
    issues = validate_config()
    if issues:
        print("\\n=== Configuration Warnings/Errors ===")
        for issue in issues:
            print(issue)
        print("=" * 40 + "\\n")
    
    logger.info("Note: ML models will be loaded on first use to optimize startup time")
    
    init_all_databases()
    kb_listener, ms_listener = start_listeners()
    
    if not kb_listener or not ms_listener:
        logger.error("Failed to start input listeners")
        return
    
    # Start session
    tracker_instance.start_session()
    
    ocr_counter = audio_counter = webcam_counter = save_counter = 0
    ocr_result = {'keywords': {}}
    audio_result = {'audio_label': 'silence'}
    
    try:
        while not stop_event.is_set():
            try:
                cycle_start = time.time()
                
                # Active window
                window_title, interaction_rate = get_active_window()
                
                # Audio processing with lazy loading
                audio_counter += TRACK_INTERVAL
                if audio_counter >= AUDIO_INTERVAL:
                    try:
                        audio_pipeline = get_audio_pipeline()
                        audio_result = audio_pipeline()
                        logger.debug(f"Audio: {audio_result.get('audio_label', 'silence')}")
                    except Exception as e:
                        logger.warning(f"Audio processing error: {e}")
                    audio_counter = 0
                
                # OCR processing with lazy loading
                ocr_counter += TRACK_INTERVAL
                if ocr_counter >= SCREENSHOT_INTERVAL:
                    try:
                        ocr_pipeline = get_ocr_pipeline()
                        ocr_result = ocr_pipeline()
                        if ocr_result:
                            keywords = ocr_result.get('keywords', {})
                            tracker_instance.process_concepts(keywords)
                            logger.debug(f"OCR: {len(keywords)} keywords")
                    except Exception as e:
                        logger.warning(f"OCR processing error: {e}")
                    ocr_counter = 0
                
                # Webcam processing with lazy loading
                webcam_counter += TRACK_INTERVAL
                if webcam_counter >= WEBCAM_INTERVAL and webcam_enabled:
                    try:
                        webcam_pipeline = get_webcam_pipeline()
                        webcam_result = webcam_pipeline()
                        attention = webcam_result.get('attentiveness_score', 0)
                        tracker_instance.update_attention(attention)
                        logger.debug(f"Webcam: Attention {attention:.1f}")
                    except Exception as e:
                        logger.warning(f"Webcam error: {e}")
                    webcam_counter = 0
                
                # Intent prediction
                try:
                    intent_result = predict_intent(
                        ocr_keywords=ocr_result.get('keywords', {}),
                        audio_label=audio_result.get('audio_label', 'silence'),
                        attention_score=tracker_instance.session_attention_scores[-1] if tracker_instance.session_attention_scores else 0,
                        interaction_rate=interaction_rate,
                        use_webcam=webcam_enabled
                    )
                    tracker_instance.process_intent(intent_result, context=window_title)
                except Exception as e:
                    logger.warning(f"Intent prediction error: {e}")
                
                # Periodic analytics save
                save_counter += TRACK_INTERVAL
                if save_counter >= 300:
                    tracker_instance.export_tracking_data()
                    save_counter = 0
                
                # Maintain loop interval
                cycle_time = time.time() - cycle_start
                sleep_time = max(0.1, TRACK_INTERVAL - cycle_time)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(TRACK_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("Tracking interrupted by user")
    
    finally:
        tracker_instance.end_session()
        
        try:
            if kb_listener:
                kb_listener.stop()
            if ms_listener:
                ms_listener.stop()
        except Exception as e:
            logger.error(f"Error stopping listeners: {e}")
        
        logger.info("Tracker shutdown complete")


if __name__ == "__main__":
    stop_event = Event()
    allow_camera = ask_user_permissions()
    track_loop(stop_event, webcam_enabled=allow_camera)