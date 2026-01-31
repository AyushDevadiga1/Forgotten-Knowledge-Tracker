# core/tracker.py - COMPLETELY REWRITTEN
import time
import sqlite3
import json
import pickle
import os
import threading
from threading import Event, Lock
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import cv2
import numpy as np
from pynput import keyboard, mouse
import win32gui
from plyer import notification

from core.db_module import init_all_databases
from config import DB_PATH, TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL, USER_ALLOW_WEBCAM
from core.ocr_module import ocr_pipeline
from core.audio_module import record_audio, classify_audio,audio_pipeline
from core.webcam_module import webcam_pipeline
from core.intent_module import predict_intent
from core.knowledge_graph import add_concepts, get_graph, add_edges
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve
from core.face_detection_module import FaceDetector

class ThreadSafeCounter:
    """Thread-safe counter for keyboard and mouse events"""
    def __init__(self):
        self._value = 0
        self._lock = Lock()
    
    def increment(self):
        with self._lock:
            self._value += 1
    
    def get_and_reset(self):
        with self._lock:
            value = self._value
            self._value = 0
            return value
    
    def get_value(self):
        with self._lock:
            return self._value
    
    # Add this method for debugging
    def debug_info(self):
        with self._lock:
            return f"Value: {self._value}"
        

# Global counters with thread safety
keyboard_counter = ThreadSafeCounter()
mouse_counter = ThreadSafeCounter()

# Load classifiers with error handling
def load_audio_classifier():
    """Load audio classifier safely"""
    audio_clf_path = "core/audio_classifier.pkl"
    if os.path.exists(audio_clf_path):
        try:
            with open(audio_clf_path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Failed to load audio classifier: {e}")
    return None

def load_intent_classifier():
    """Load intent classifier safely"""
    intent_clf_path = "core/intent_classifier.pkl"
    intent_map_path = "core/intent_label_map.pkl"
    
    if os.path.exists(intent_clf_path) and os.path.exists(intent_map_path):
        try:
            with open(intent_clf_path, "rb") as f:
                clf = pickle.load(f)
            with open(intent_map_path, "rb") as f:
                label_map = pickle.load(f)
            return clf, label_map
        except Exception as e:
            print(f"Failed to load intent classifier: {e}")
    
    return None, None

# Load classifiers at startup
audio_clf = load_audio_classifier()
intent_clf, intent_label_map = load_intent_classifier()

# Event handlers
def on_key_press(key):
    keyboard_counter.increment()

def on_mouse_click(x, y, button, pressed):
    if pressed:
        mouse_counter.increment()

def start_listeners():
    """Start keyboard and mouse listeners"""
    try:
        kb_listener = keyboard.Listener(on_press=on_key_press)
        ms_listener = mouse.Listener(on_click=on_mouse_click)
        kb_listener.start()
        ms_listener.start()
        return kb_listener, ms_listener
    except Exception as e:
        print(f"Error starting listeners: {e}")
        return None, None

def get_active_window():
    """Get current active window safely"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or "Unknown"
        
        # Calculate interaction rate (events per interval)
        total_events = keyboard_counter.get_value() + mouse_counter.get_value()
        interaction_rate = min(total_events / TRACK_INTERVAL if TRACK_INTERVAL > 0 else 0, 100)  # Cap at 100
        
        return title, interaction_rate
    except Exception as e:
        print(f"Error getting active window: {e}")
        return "Unknown", 0

def log_session(window_title, interaction_rate):
    """Log session to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        app_name = window_title.split(" - ")[-1] if " - " in window_title else window_title

        c.execute("""INSERT INTO sessions 
                     (start_ts, end_ts, app_name, window_title, interaction_rate) 
                     VALUES (?, ?, ?, ?, ?)""",
                  (ts, ts, app_name, window_title, float(interaction_rate)))
        conn.commit()
        print(f"Logged session: {app_name[:50]}, Interactions: {interaction_rate:.1f}/s")
    except Exception as e:
        print(f"Failed to log session: {e}")
    finally:
        conn.close()
        # Reset counters after logging
        keyboard_counter.get_and_reset()
        mouse_counter.get_and_reset()

def log_multi_modal(data: Dict[str, Any]):
    """Log multi-modal data to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Safely prepare OCR data
        ocr_keywords = data.get('ocr_keywords', {})
        if not isinstance(ocr_keywords, dict):
            ocr_keywords = {}
        
        ocr_data_to_store = {}
        for kw, info in ocr_keywords.items():
            try:
                if isinstance(info, dict):
                    score = float(info.get("score", 0.5))
                    count = int(info.get("count", 1))
                else:
                    score = float(info)
                    count = 1
                ocr_data_to_store[str(kw)] = {"score": score, "count": count}
            except (ValueError, TypeError):
                continue

        c.execute('''
            INSERT INTO multi_modal_logs
            (timestamp, window_title, ocr_keywords, audio_label, attention_score, 
             interaction_rate, intent_label, intent_confidence, memory_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            data.get('window_title', ''),
            json.dumps(ocr_data_to_store),
            data.get('audio_label', 'silence'),
            float(data.get('attention_score', 0)),
            float(data.get('interaction_rate', 0)),
            data.get('intent_label', 'unknown'),
            float(data.get('intent_confidence', 0)),
            float(data.get('memory_score', 0))
        ))
        conn.commit()
    except Exception as e:
        print(f"Failed to write multi_modal_logs: {e}")
    finally:
        conn.close()

def save_knowledge_graph():
    """Save knowledge graph to file"""
    try:
        G = get_graph()
        os.makedirs("data", exist_ok=True)
        with open("data/knowledge_graph.pkl", "wb") as f:
            pickle.dump(G, f)
        print("Knowledge graph saved.")
    except Exception as e:
        print(f"Error saving knowledge graph: {e}")

def load_knowledge_graph():
    """Load knowledge graph from file"""
    try:
        graph_path = "data/knowledge_graph.pkl"
        if os.path.exists(graph_path):
            with open(graph_path, "rb") as f:
                return pickle.load(f)
    except Exception as e:
        print(f"Error loading knowledge graph: {e}")
    return get_graph()

def classify_audio_live():
    """Classify audio in real-time"""
    try:
        audio_data = record_audio()
        if audio_clf:
            label, confidence = classify_audio(audio_data)
            return label, confidence
        else:
            # Fallback: simple energy-based detection
            rms = np.sqrt(np.mean(audio_data**2))
            if rms > 0.1:
                return "speech", 0.6
            elif rms > 0.01:
                return "music", 0.4
            else:
                return "silence", 0.8
    except Exception as e:
        print(f"Audio classification failed: {e}")
        return "unknown", 0.0

def process_ocr_data():
    """Process OCR data and update knowledge graph"""
    try:
        ocr_result = ocr_pipeline()
        if not ocr_result:
            return {}
            
        keywords = ocr_result.get('keywords', {})
        
        # Convert to safe format
        safe_keywords = {}
        for kw, info in keywords.items():
            try:
                if isinstance(info, dict):
                    score = float(info.get("score", 0.5))
                    count = int(info.get("count", 1))
                else:
                    score = float(info)
                    count = 1
                safe_keywords[str(kw)] = {"score": score, "count": count}
            except (ValueError, TypeError):
                continue
        
        # Add concepts to knowledge graph
        if safe_keywords:
            add_concepts(list(safe_keywords.keys()))
            print(f"OCR extracted {len(safe_keywords)} keywords")
        
        return safe_keywords
    except Exception as e:
        print(f"OCR processing error: {e}")
        return {}

def update_memory_scores(ocr_keywords: Dict[str, Any], attention_score: float, audio_label: str):
    """Update memory scores for OCR keywords"""
    G = get_graph()
    max_memory_score = 0.0
    
    for concept, info in ocr_keywords.items():
        try:
            if not concept or concept not in G.nodes:
                add_concepts([concept])
                G = get_graph()
                if concept not in G.nodes:
                    continue

            # Get or initialize node data
            node_data = G.nodes[concept]
            last_review_str = node_data.get('last_review')
            
            # Parse last review time
            if last_review_str and isinstance(last_review_str, str):
                try:
                    last_review = datetime.fromisoformat(last_review_str)
                except:
                    last_review = datetime.now()
            else:
                last_review = datetime.now()

            # Compute memory score
            lambda_val = 0.1
            intent_conf = float(node_data.get('intent_conf', 1.0))
            audio_conf = 1.0 if audio_label == "speech" else 0.7
            
            mem_score = compute_memory_score(
                last_review, lambda_val, intent_conf, attention_score, audio_conf
            )
            
            # Update node with new memory data
            next_review = schedule_next_review(last_review, mem_score, lambda_val)
            
            G.nodes[concept].update({
                'memory_score': float(mem_score),
                'next_review_time': next_review.isoformat() if isinstance(next_review, datetime) else str(next_review),
                'last_review': datetime.now().isoformat(),
                'intent_conf': float(intent_conf)
            })
            
            max_memory_score = max(max_memory_score, mem_score)
            
            # Log forgetting curve
            log_forgetting_curve(concept, last_review, observed_usage=info.get('count', 1))
            
        except Exception as e:
            print(f"Error updating memory for {concept}: {e}")
    
    return max_memory_score

def track_loop(stop_event: Optional[Event] = None):
    """Main tracking loop with enhanced audio & webcam"""
    if stop_event is None:
        stop_event = Event()

    # Initialize databases
    init_all_databases()
    
    # Start input listeners
    kb_listener, ms_listener = start_listeners()
    if not kb_listener or not ms_listener:
        print("Failed to start input listeners")
        return

    # Load existing knowledge graph
    G = load_knowledge_graph()

    # State variables
    ocr_counter = audio_counter = webcam_counter = save_counter = 0
    latest_data = {
        'ocr_keywords': {},
        'audio_label': 'silence',
        'audio_confidence': 0.0,
        'attention_score': 0,
        'interaction_rate': 0,
        'window_title': 'Unknown'
    }

    print("Starting enhanced tracking loop...")

    try:
        while not stop_event.is_set():
            cycle_start = time.time()

            try:
                # -----------------------
                # Active window & interaction
                # -----------------------
                window_title, interaction_rate = get_active_window()
                latest_data['window_title'] = window_title
                latest_data['interaction_rate'] = interaction_rate
                
                # Log session
                log_session(window_title, interaction_rate)

                # -----------------------
                # Audio processing
                # -----------------------
                audio_counter += TRACK_INTERVAL
                if audio_counter >= AUDIO_INTERVAL:
                    audio_result = audio_pipeline()  # Enhanced audio
                    latest_data['audio_label'] = audio_result.get('audio_label', 'silence')
                    latest_data['audio_confidence'] = audio_result.get('confidence', 0.0)
                    audio_counter = 0
                    print(f"Audio: {latest_data['audio_label']} (conf: {latest_data['audio_confidence']:.2f})")

                # -----------------------
                # OCR processing
                # -----------------------
                ocr_counter += TRACK_INTERVAL
                if ocr_counter >= SCREENSHOT_INTERVAL:
                    ocr_keywords = process_ocr_data()
                    latest_data['ocr_keywords'] = ocr_keywords
                    ocr_counter = 0

                # -----------------------
                # Webcam processing
                # -----------------------
                webcam_counter += TRACK_INTERVAL
                if webcam_counter >= WEBCAM_INTERVAL and USER_ALLOW_WEBCAM:
                    try:
                        webcam_result = webcam_pipeline()  # Enhanced webcam
                        attention_score = webcam_result.get('attentiveness_score', 0)
                        face_count = webcam_result.get('face_count', 0)
                        latest_data['attention_score'] = attention_score
                        print(f"Webcam: Attention {attention_score:.1f}, Faces: {face_count}")
                        webcam_counter = 0
                    except Exception as e:
                        print(f"Webcam processing error: {e}")
                        latest_data['attention_score'] = 0
                        webcam_counter = 0

                # -----------------------
                # Update memory scores
                # -----------------------
                memory_score = update_memory_scores(
                    latest_data['ocr_keywords'],
                    latest_data['attention_score'],
                    latest_data['audio_label']
                )
                latest_data['memory_score'] = memory_score

                # -----------------------
                # Intent prediction
                # -----------------------
                intent_result = predict_intent(
                    ocr_keywords=latest_data['ocr_keywords'],
                    audio_label=latest_data['audio_label'],
                    attention_score=latest_data['attention_score'],
                    interaction_rate=latest_data['interaction_rate'],
                    use_webcam=USER_ALLOW_WEBCAM
                )
                latest_data['intent_label'] = intent_result['intent_label']
                latest_data['intent_confidence'] = intent_result['confidence']
                print(f"Intent: {intent_result['intent_label']} (conf: {intent_result['confidence']:.2f})")

                # -----------------------
                # Add edges to knowledge graph
                # -----------------------
                try:
                    add_edges(
                        latest_data['ocr_keywords'],
                        latest_data['audio_label'],
                        latest_data['intent_label']
                    )
                except Exception as e:
                    print(f"Failed to add edges: {e}")

                # -----------------------
                # Log multi-modal data
                # -----------------------
                log_multi_modal(latest_data)

                # -----------------------
                # Periodic knowledge graph save
                # -----------------------
                save_counter += TRACK_INTERVAL
                if save_counter >= 300:  # Every 5 minutes
                    save_knowledge_graph()
                    save_counter = 0

                # -----------------------
                # Maintain consistent loop interval
                # -----------------------
                cycle_time = time.time() - cycle_start
                sleep_time = max(0.1, TRACK_INTERVAL - cycle_time)
                time.sleep(sleep_time)

            except KeyboardInterrupt:
                print("Tracker stopped by user (KeyboardInterrupt).")
                break
            except Exception as e:
                print(f"Unexpected error in tracking loop: {e}")
                time.sleep(TRACK_INTERVAL)  # Prevent tight error loop

    finally:
        # -----------------------
        # Cleanup
        # -----------------------
        print("Shutting down tracker...")
        save_knowledge_graph()
        try:
            if kb_listener:
                kb_listener.stop()
            if ms_listener:
                ms_listener.stop()
        except:
            pass
        print("Tracker shutdown complete.")

def ask_user_permissions():
    """Ask for user permissions"""
    global USER_ALLOW_WEBCAM
    try:
        choice = input("Do you want to enable webcam attention tracking? (y/n): ").lower().strip()
        USER_ALLOW_WEBCAM = choice in ['y', 'yes', '1']
        print(f"Webcam tracking: {'ENABLED' if USER_ALLOW_WEBCAM else 'DISABLED'}")
    except:
        USER_ALLOW_WEBCAM = False
        print("Webcam tracking disabled by default")

if __name__ == "__main__":
    ask_user_permissions()
    track_loop()