import time
import os
import sqlite3
import json
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional
import logging

from tracker_app.config import DATA_DIR
from tracker_app.core.concept_scheduler import ConceptScheduler

logger = logging.getLogger("ActivityMonitor")


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


class ActivityMonitor:
    """Main enhanced tracker combining all improvements (formerly EnhancedActivityTracker)"""
    
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
