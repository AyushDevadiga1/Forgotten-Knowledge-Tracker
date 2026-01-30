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

from core.db_module import init_all_databases, get_db_connection
from config import DB_PATH, TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL, validate_config, DATA_DIR
from core.intent_module import predict_intent
from core.knowledge_graph import add_concepts, get_graph, add_edges

# Lazy-loaded modules (loaded on first use to optimize startup time)
_ocr_pipeline = None
_audio_pipeline = None
_webcam_pipeline = None

def get_ocr_pipeline():
    """Lazy load OCR pipeline"""
    global _ocr_pipeline
    if _ocr_pipeline is None:
        logger.info("Loading OCR pipeline...")
        from core.ocr_module import ocr_pipeline
        _ocr_pipeline = ocr_pipeline
    return _ocr_pipeline

def get_audio_pipeline():
    """Lazy load audio pipeline"""
    global _audio_pipeline
    if _audio_pipeline is None:
        logger.info("Loading audio pipeline...")
        from core.audio_module import audio_pipeline
        _audio_pipeline = audio_pipeline
    return _audio_pipeline

def get_webcam_pipeline():
    """Lazy load webcam pipeline"""
    global _webcam_pipeline
    if _webcam_pipeline is None:
        logger.info("Loading webcam pipeline...")
        from core.webcam_module import webcam_pipeline
        _webcam_pipeline = webcam_pipeline
    return _webcam_pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Tracker")


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


class ConceptScheduler:
    """SM-2 inspired scheduling for tracked concepts"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DATA_DIR / "tracking_concepts.db")
        self._init_db()
    
    def _init_db(self):
        """Initialize concept tracking database"""
        os.makedirs(os.path.dirname(self.db_path) or "data", exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS tracked_concepts (
                id TEXT PRIMARY KEY,
                concept TEXT UNIQUE,
                first_seen TEXT,
                last_seen TEXT,
                encounter_count INTEGER DEFAULT 1,
                sm2_interval REAL DEFAULT 1,
                sm2_ease REAL DEFAULT 2.5,
                next_review TEXT,
                relevance_score REAL DEFAULT 0.5,
                priority INTEGER DEFAULT 5
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS concept_encounters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept_id TEXT,
                timestamp TEXT,
                context TEXT,
                confidence REAL,
                FOREIGN KEY(concept_id) REFERENCES tracked_concepts(id)
            )
        ''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_concept_timestamp ON concept_encounters(concept_id, timestamp)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_next_review ON tracked_concepts(next_review)')
        
        conn.commit()
        conn.close()
    
    def add_concept(self, concept: str, confidence: float = 0.5, context: str = "") -> str:
        """Add or update a tracked concept"""
        import uuid
        concept_id = f"{concept}_{int(time.time())}" if not hasattr(self, '_id_map') else self._id_map.get(concept, str(uuid.uuid4()))
        
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        now = datetime.now().isoformat()
        
        c.execute('SELECT id FROM tracked_concepts WHERE concept = ?', (concept,))
        existing = c.fetchone()
        
        if existing:
            concept_id = existing[0]
            c.execute('''
                UPDATE tracked_concepts 
                SET last_seen = ?, encounter_count = encounter_count + 1,
                    relevance_score = (relevance_score + ?) / 2
                WHERE id = ?
            ''', (now, confidence, concept_id))
        else:
            c.execute('''
                INSERT INTO tracked_concepts 
                (id, concept, first_seen, last_seen, next_review, relevance_score)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (concept_id, concept, now, now, now, confidence))
        
        # Log encounter
        c.execute('''
            INSERT INTO concept_encounters (concept_id, timestamp, context, confidence)
            VALUES (?, ?, ?, ?)
        ''', (concept_id, now, context, confidence))
        
        conn.commit()
        conn.close()
        
        return concept_id
    
    def schedule_next_review(self, concept_id: str, quality: int = 3):
        """
        Schedule next review using SM-2 algorithm
        quality: 0-5 (0=fail, 5=perfect)
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('SELECT sm2_interval, sm2_ease FROM tracked_concepts WHERE id = ?', (concept_id,))
        row = c.fetchone()
        
        if not row:
            conn.close()
            return
        
        interval, ease = row
        
        # SM-2 algorithm
        if quality < 3:
            new_interval = 1
            new_ease = max(1.3, ease - 0.2)
        else:
            if interval == 1:
                new_interval = 3
            else:
                new_interval = interval * ease
            new_ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            new_ease = max(1.3, new_ease)
        
        next_review = datetime.now() + timedelta(days=new_interval)
        
        c.execute('''
            UPDATE tracked_concepts 
            SET sm2_interval = ?, sm2_ease = ?, next_review = ?
            WHERE id = ?
        ''', (new_interval, new_ease, next_review.isoformat(), concept_id))
        
        conn.commit()
        conn.close()
    
    def get_due_concepts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get concepts due for review"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        now = datetime.now().isoformat()
        c.execute('''
            SELECT id, concept, encounter_count, sm2_interval, relevance_score
            FROM tracked_concepts
            WHERE next_review <= ?
            ORDER BY relevance_score DESC, next_review ASC
            LIMIT ?
        ''', (now, limit))
        
        concepts = [
            {
                'id': row[0],
                'concept': row[1],
                'encounter_count': row[2],
                'interval': row[3],
                'relevance': row[4]
            }
            for row in c.fetchall()
        ]
        
        conn.close()
        return concepts
    
    def get_concept_history(self, concept: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get encounter history for a concept"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        c.execute('''
            SELECT ce.timestamp, ce.context, ce.confidence, tc.relevance_score
            FROM concept_encounters ce
            JOIN tracked_concepts tc ON ce.concept_id = tc.id
            WHERE tc.concept = ? AND ce.timestamp >= ?
            ORDER BY ce.timestamp DESC
        ''', (concept, start_date))
        
        history = [
            {
                'timestamp': row[0],
                'context': row[1],
                'confidence': row[2],
                'relevance': row[3]
            }
            for row in c.fetchall()
        ]
        
        conn.close()
        return history


class IntentValidator:
    """Validates and improves intent predictions over time"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DATA_DIR / "intent_validation.db")
        self._init_db()
        self.prediction_buffer = []
    
    def _init_db(self):
        """Initialize intent validation database"""
        os.makedirs(os.path.dirname(self.db_path) or "data", exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS intent_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                predicted_intent TEXT,
                confidence REAL,
                context_keywords TEXT,
                user_feedback INTEGER,
                feedback_timestamp TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS intent_accuracy (
                intent TEXT PRIMARY KEY,
                total_predictions INTEGER DEFAULT 0,
                correct_predictions INTEGER DEFAULT 0,
                accuracy REAL DEFAULT 0.0,
                last_updated TEXT
            )
        ''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_intent_timestamp ON intent_predictions(timestamp)')
        
        conn.commit()
        conn.close()
    
    def log_prediction(self, predicted_intent: str, confidence: float, context: str):
        """Log an intent prediction"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO intent_predictions 
            (timestamp, predicted_intent, confidence, context_keywords)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now().isoformat(), predicted_intent, confidence, context))
        
        conn.commit()
        conn.close()
        
        self.prediction_buffer.append({
            'intent': predicted_intent,
            'confidence': confidence,
            'timestamp': datetime.now()
        })
    
    def log_feedback(self, prediction_id: int, correct: bool):
        """User provides feedback on prediction accuracy"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('''
            UPDATE intent_predictions 
            SET user_feedback = ?, feedback_timestamp = ?
            WHERE id = ?
        ''', (1 if correct else 0, datetime.now().isoformat(), prediction_id))
        
        # Update accuracy stats
        c.execute('SELECT predicted_intent FROM intent_predictions WHERE id = ?', (prediction_id,))
        intent = c.fetchone()[0]
        
        c.execute('''
            INSERT OR IGNORE INTO intent_accuracy (intent, total_predictions, correct_predictions)
            VALUES (?, 1, ?)
        ''', (intent, 1 if correct else 0))
        
        c.execute('''
            UPDATE intent_accuracy 
            SET total_predictions = total_predictions + 1,
                correct_predictions = correct_predictions + ?,
                accuracy = CAST(correct_predictions + ? AS REAL) / (total_predictions + 1),
                last_updated = ?
            WHERE intent = ?
        ''', (1 if correct else 0, 1 if correct else 0, datetime.now().isoformat(), intent))
        
        conn.commit()
        conn.close()
    
    def get_accuracy_stats(self) -> Dict[str, Any]:
        """Get overall intent prediction accuracy"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('''
            SELECT AVG(accuracy), COUNT(*), MAX(accuracy), MIN(accuracy)
            FROM intent_accuracy
            WHERE total_predictions >= 5
        ''')
        
        row = c.fetchone()
        avg_acc = row[0] or 0.5
        intent_count = row[1] or 0
        
        result = {
            'average_accuracy': avg_acc,
            'intents_tracked': intent_count,
            'best_accuracy': row[2] or 0,
            'worst_accuracy': row[3] or 0
        }
        
        conn.close()
        return result


class TrackingAnalytics:
    """Analytics on tracked concepts and sessions"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DATA_DIR / "tracking_analytics.db")
        self._init_db()
    
    def _init_db(self):
        """Initialize analytics database"""
        os.makedirs(os.path.dirname(self.db_path) or "data", exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS tracking_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT,
                end_time TEXT,
                duration_minutes REAL,
                concepts_encountered INTEGER,
                avg_attention REAL,
                primary_activity TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                total_tracking_minutes REAL,
                concepts_encountered INTEGER,
                avg_attention REAL,
                primary_intents TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_session(self, start_time: datetime, end_time: datetime, 
                   concepts_count: int, avg_attention: float, primary_activity: str):
        """Log a tracking session"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        duration = (end_time - start_time).total_seconds() / 60
        
        c.execute('''
            INSERT INTO tracking_sessions 
            (start_time, end_time, duration_minutes, concepts_encountered, avg_attention, primary_activity)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (start_time.isoformat(), end_time.isoformat(), duration, concepts_count, avg_attention, primary_activity))
        
        conn.commit()
        conn.close()
    
    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get daily tracking summary"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT SUM(duration_minutes), SUM(concepts_encountered), AVG(avg_attention)
            FROM tracking_sessions
            WHERE DATE(start_time) = ?
        ''', (date_str,))
        
        row = c.fetchone()
        
        summary = {
            'date': date_str,
            'total_minutes': row[0] or 0,
            'concepts': row[1] or 0,
            'avg_attention': row[2] or 0
        }
        
        conn.close()
        return summary
    
    def get_trend_analysis(self, days: int = 7) -> Dict[str, Any]:
        """Analyze tracking trends"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        c.execute('''
            SELECT 
                COUNT(DISTINCT DATE(start_time)) as tracking_days,
                AVG(duration_minutes) as avg_session_length,
                SUM(concepts_encountered) as total_concepts,
                AVG(avg_attention) as avg_attention
            FROM tracking_sessions
            WHERE start_time >= ?
        ''', (start_date,))
        
        row = c.fetchone()
        
        result = {
            'tracking_days': row[0] or 0,
            'avg_session_minutes': row[1] or 0,
            'total_concepts_encountered': row[2] or 0,
            'avg_attention_score': row[3] or 0
        }
        
        conn.close()
        return result


class EnhancedActivityTracker:
    """Main enhanced tracker combining all improvements"""
    
    def __init__(self):
        self.scheduler = ConceptScheduler()
        self.validator = IntentValidator()
        self.analytics = TrackingAnalytics()
        
        self.keyboard_counter = ThreadSafeCounter()
        self.mouse_counter = ThreadSafeCounter()
        
        self.session_start = None
        self.session_concepts = []
        self.session_attention_scores = []
        
        # State tracking
        self.is_running = False
        self._lock = Lock()
    
    def start_session(self):
        """Start a tracking session"""
        with self._lock:
            self.session_start = datetime.now()
            self.session_concepts = []
            self.session_attention_scores = []
            self.is_running = True
        logger.info(f"Tracking session started at {self.session_start}")
    
    def end_session(self):
        """End tracking session and save analytics"""
        with self._lock:
            if not self.is_running:
                return
            
            session_end = datetime.now()
            
            # Calculate session stats
            concepts_count = len(set(self.session_concepts))
            avg_attention = sum(self.session_attention_scores) / len(self.session_attention_scores) if self.session_attention_scores else 0
            
            # Determine primary activity
            primary_activity = "general_browsing"
            if self.session_concepts:
                from collections import Counter
                activity_counts = Counter(self.session_concepts)
                primary_activity = activity_counts.most_common(1)[0][0]
            
            # Log to analytics
            self.analytics.log_session(
                self.session_start,
                session_end,
                concepts_count,
                avg_attention,
                primary_activity
            )
            
            self.is_running = False
            
        logger.info(f"Tracking session ended. Concepts: {concepts_count}, Avg Attention: {avg_attention:.2f}")
    
    def process_concepts(self, ocr_keywords: Dict[str, Any], confidence: float = 0.6):
        """Process and schedule encountered concepts"""
        for concept, info in ocr_keywords.items():
            if not concept or len(concept) < 2:
                continue
            
            try:
                concept_conf = float(info.get('score', confidence))
                self.scheduler.add_concept(concept, concept_conf, context="ocr")
                self.session_concepts.append(concept)
            except Exception as e:
                logger.error(f"Error processing concept {concept}: {e}")
    
    def process_intent(self, intent_result: Dict[str, Any], context: str = ""):
        """Process intent prediction with validation"""
        intent = intent_result.get('intent_label', 'unknown')
        confidence = intent_result.get('confidence', 0.5)
        
        # Log for validation
        self.validator.log_prediction(intent, confidence, context)
    
    def update_attention(self, attention_score: float):
        """Track attention/focus levels"""
        self.session_attention_scores.append(attention_score)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        with self._lock:
            if not self.is_running or not self.session_start:
                return {}
            
            elapsed = (datetime.now() - self.session_start).total_seconds() / 60
            
            return {
                'session_duration_minutes': elapsed,
                'concepts_encountered': len(set(self.session_concepts)),
                'avg_attention': sum(self.session_attention_scores) / len(self.session_attention_scores) if self.session_attention_scores else 0,
                'is_active': self.is_running
            }
    
    def get_concept_recommendations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top concepts to review"""
        return self.scheduler.get_due_concepts(limit)
    
    def export_tracking_data(self, output_file: str = "data/tracking_export.json"):
        """Export all tracking data"""
        due_concepts = self.scheduler.get_due_concepts(1000)
        intent_stats = self.validator.get_accuracy_stats()
        daily_stats = self.analytics.get_daily_summary()
        trend_stats = self.analytics.get_trend_analysis(30)
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'session_stats': self.get_session_stats(),
            'due_concepts': due_concepts,
            'intent_accuracy': intent_stats,
            'daily_summary': daily_stats,
            'trend_analysis': trend_stats
        }
        
        os.makedirs(os.path.dirname(output_file) or "data", exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Tracking data exported to {output_file}")
        return export_data


# Global tracker instance
tracker_instance = EnhancedActivityTracker()


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