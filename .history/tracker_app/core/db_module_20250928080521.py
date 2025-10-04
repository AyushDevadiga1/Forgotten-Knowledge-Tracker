import sqlite3
from config import DB_PATH, ENHANCED_DB_PATH  # NEW: Enhanced DB path
from datetime import datetime, timedelta
import json
import logging
import os

logger = logging.getLogger(__name__)

# NEW: Ensure data directory exists
def ensure_data_directory():
    """Create data directory if it doesn't exist"""
    data_dir = os.path.dirname(ENHANCED_DB_PATH)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.info(f"Created data directory: {data_dir}")

# NEW: Encryption module
try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None
    logger.warning("cryptography not installed. Encryption disabled.")

class DataEncryptor:
    def __init__(self, key_path="./data/encryption.key"):
        ensure_data_directory()  # Ensure directory exists
        self.key_path = key_path
        self.key = self._load_or_generate_key()
        self.fernet = Fernet(self.key) if Fernet else None
    
    def _load_or_generate_key(self):
        try:
            with open(self.key_path, 'rb') as key_file:
                return key_file.read()
        except FileNotFoundError:
            if Fernet:
                key = Fernet.generate_key()
                with open(self.key_path, 'wb') as key_file:
                    key_file.write(key)
                return key
            return None
    
    def encrypt_data(self, data):
        """Encrypt sensitive data before storage"""
        if not self.fernet or data is None:
            return data
        if isinstance(data, dict):
            data = json.dumps(data)
        return self.fernet.encrypt(data.encode())
    
    def decrypt_data(self, encrypted_data):
        """Decrypt data for display/processing"""
        if not self.fernet or encrypted_data is None:
            return encrypted_data
        try:
            decrypted = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted.decode())
        except:
            return encrypted_data

# ORIGINAL FUNCTION - PRESERVED (uses original DB)
def init_db():
    """Initialize ORIGINAL database (sessions.db)"""
    ensure_data_directory()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ORIGINAL: Table for session/activity logging
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_ts TEXT,
                    end_ts TEXT,
                    app_name TEXT,
                    window_title TEXT,
                    interaction_rate REAL
                )''')
    
    conn.commit()
    conn.close()
    logger.info(f"Original database initialized: {DB_PATH}")
# Add this to db_module.py in the init_enhanced_db() function
def init_enhanced_db():
    """Initialize ENHANCED database (enhanced_sessions.db)"""
    ensure_data_directory()
    conn = sqlite3.connect(ENHANCED_DB_PATH)
    c = conn.cursor()

    # FIXED: Corrected table name from 'enhanced_sessions' to 'sessions_enhanced'
    c.execute('''CREATE TABLE IF NOT EXISTS sessions_enhanced (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    window_title TEXT,
                    app_type TEXT,
                    interaction_rate REAL,
                    ocr_keywords TEXT,
                    ocr_confidence REAL,
                    audio_label TEXT,
                    audio_confidence REAL,
                    attention_score REAL,
                    intent_label TEXT,
                    intent_confidence REAL,
                    intent_method TEXT,
                    memory_score REAL,
                    algorithm_version TEXT DEFAULT 'novel_v1',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # ... rest of the function remains the same
    # NEW: Concept memory predictions table
    c.execute('''CREATE TABLE IF NOT EXISTS concept_memory_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    concept TEXT,
                    memory_score REAL,
                    next_review_time TEXT,
                    prediction_method TEXT,
                    ocr_confidence REAL,
                    audio_confidence REAL,
                    attention_score REAL,
                    interaction_rate REAL,
                    app_type TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(session_id) REFERENCES enhanced_sessions(id)
                )''')
    
    # NEW: Algorithm performance tracking
    c.execute('''CREATE TABLE IF NOT EXISTS algorithm_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    algorithm_name TEXT,
                    metric_name TEXT,
                    metric_value REAL,
                    timestamp TEXT,
                    sample_size INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # NEW: User preferences and consent
    c.execute('''CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ocr_enabled BOOLEAN DEFAULT 1,
                    audio_enabled BOOLEAN DEFAULT 0,
                    webcam_enabled BOOLEAN DEFAULT 0,
                    novel_algorithms_enabled BOOLEAN DEFAULT 1,
                    data_retention_days INTEGER DEFAULT 30,
                    consent_given BOOLEAN DEFAULT 0,
                    consent_timestamp TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # NEW: Knowledge graph concepts (separate from original)
    c.execute('''CREATE TABLE IF NOT EXISTS enhanced_concepts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept TEXT UNIQUE,
                    embedding BLOB,
                    encounter_count INTEGER DEFAULT 1,
                    avg_memory_score REAL DEFAULT 0.3,
                    last_encounter_time TEXT,
                    next_review_time TEXT,
                    algorithm_metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # NEW: Reminder history
    c.execute('''CREATE TABLE IF NOT EXISTS reminder_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept TEXT,
                    memory_score REAL,
                    reminder_time TEXT,
                    review_time TEXT,
                    user_response TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )''')
    
    conn.commit()
    conn.close()
    logger.info(f"Enhanced database initialized: {ENHANCED_DB_PATH}")

# NEW: Enhanced session logging (uses enhanced DB)
def log_enhanced_session(window_title, app_type, interaction_rate, ocr_data=None, 
                        audio_data=None, attention_score=0, intent_data=None, 
                        memory_data=None, algorithm_version="novel_v1"):
    """Log session to ENHANCED database with novel algorithm data"""
    conn = sqlite3.connect(ENHANCED_DB_PATH)
    c = conn.cursor()
    
    # Prepare data
    timestamp = datetime.now().isoformat()
    ocr_keywords = str(ocr_data.get('keywords', [])) if ocr_data else None
    ocr_confidence = ocr_data.get('confidence', 0.0) if ocr_data else 0.0
    audio_label = audio_data.get('audio_label', 'silence') if audio_data else 'silence'
    audio_confidence = audio_data.get('confidence', 0.0) if audio_data else 0.0
    intent_label = intent_data.get('intent_label', 'unknown') if intent_data else 'unknown'
    intent_confidence = intent_data.get('confidence', 0.0) if intent_data else 0.0
    intent_method = intent_data.get('method', 'original') if intent_data else 'original'
    memory_score = memory_data.get('memory_score', 0.3) if memory_data else 0.3
    
    c.execute("""INSERT INTO enhanced_sessions 
                 (timestamp, window_title, app_type, interaction_rate, 
                  ocr_keywords, ocr_confidence, audio_label, audio_confidence,
                  attention_score, intent_label, intent_confidence, intent_method,
                  memory_score, algorithm_version) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (timestamp, window_title, app_type, interaction_rate,
               ocr_keywords, ocr_confidence, audio_label, audio_confidence,
               attention_score, intent_label, intent_confidence, intent_method,
               memory_score, algorithm_version))
    
    session_id = c.lastrowid
    
    conn.commit()
    conn.close()
    
    logger.debug(f"Enhanced session logged to {ENHANCED_DB_PATH}")
    return session_id

# NEW: Log concept memory predictions
def log_concept_memory_prediction(session_id, concept, memory_score, next_review_time, 
                                 prediction_method, ocr_confidence, audio_confidence, 
                                 attention_score, interaction_rate, app_type):
    """Log individual concept memory predictions"""
    conn = sqlite3.connect(ENHANCED_DB_PATH)
    c = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    
    c.execute("""INSERT INTO concept_memory_predictions 
                 (session_id, concept, memory_score, next_review_time, prediction_method,
                  ocr_confidence, audio_confidence, attention_score, interaction_rate, app_type, timestamp)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (session_id, concept, memory_score, next_review_time.isoformat(), prediction_method,
               ocr_confidence, audio_confidence, attention_score, interaction_rate, app_type, timestamp))
    
    conn.commit()
    conn.close()

# NEW: Update enhanced concepts table
def update_enhanced_concept(concept, memory_score, next_review_time, algorithm_metadata=None):
    """Update or insert concept in enhanced concepts table"""
    conn = sqlite3.connect(ENHANCED_DB_PATH)
    c = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    algorithm_metadata_str = json.dumps(algorithm_metadata) if algorithm_metadata else None
    
    # Check if concept exists
    c.execute("SELECT id, encounter_count, avg_memory_score FROM enhanced_concepts WHERE concept = ?", (concept,))
    result = c.fetchone()
    
    if result:
        # Update existing concept
        concept_id, old_count, old_avg = result
        new_count = old_count + 1
        new_avg = ((old_avg * old_count) + memory_score) / new_count
        
        c.execute("""UPDATE enhanced_concepts 
                     SET encounter_count = ?, avg_memory_score = ?, last_encounter_time = ?,
                         next_review_time = ?, algorithm_metadata = ?, updated_at = ?
                     WHERE id = ?""",
                  (new_count, new_avg, timestamp, next_review_time.isoformat(), 
                   algorithm_metadata_str, timestamp, concept_id))
    else:
        # Insert new concept
        c.execute("""INSERT INTO enhanced_concepts 
                     (concept, avg_memory_score, last_encounter_time, next_review_time, algorithm_metadata)
                     VALUES (?, ?, ?, ?, ?)""",
                  (concept, memory_score, timestamp, next_review_time.isoformat(), algorithm_metadata_str))
    
    conn.commit()
    conn.close()

# NEW: Data retention for enhanced database
def delete_old_enhanced_data(retention_days=30):
    """Delete old data from enhanced database"""
    conn = sqlite3.connect(ENHANCED_DB_PATH)
    c = conn.cursor()
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    # Delete old enhanced sessions and related data
    c.execute("DELETE FROM enhanced_sessions WHERE timestamp < ?", (cutoff_date.isoformat(),))
    c.execute("DELETE FROM concept_memory_predictions WHERE timestamp < ?", (cutoff_date.isoformat(),))
    c.execute("DELETE FROM algorithm_performance WHERE timestamp < ?", (cutoff_date.isoformat(),))
    
    deleted_rows = conn.total_changes
    conn.commit()
    conn.close()
    
    logger.info(f"Deleted {deleted_rows} old records from enhanced database")
    return deleted_rows

# NEW: Save user preferences to enhanced database
def save_user_preferences(ocr_enabled, audio_enabled, webcam_enabled, 
                         novel_algorithms_enabled, data_retention_days, consent_given):
    """Save user preferences to enhanced database"""
    conn = sqlite3.connect(ENHANCED_DB_PATH)
    c = conn.cursor()
    
    # Clear existing preferences
    c.execute("DELETE FROM user_preferences")
    
    # Insert new preferences
    consent_timestamp = datetime.now().isoformat() if consent_given else None
    
    c.execute("""INSERT INTO user_preferences 
                 (ocr_enabled, audio_enabled, webcam_enabled, novel_algorithms_enabled, 
                  data_retention_days, consent_given, consent_timestamp)
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (ocr_enabled, audio_enabled, webcam_enabled, novel_algorithms_enabled,
               data_retention_days, consent_given, consent_timestamp))
    
    conn.commit()
    conn.close()
    logger.info("User preferences saved to enhanced database")

# NEW: Load user preferences from enhanced database
def load_user_preferences():
    """Load user preferences from enhanced database"""
    conn = sqlite3.connect(ENHANCED_DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT * FROM user_preferences ORDER BY id DESC LIMIT 1")
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'ocr_enabled': bool(result[1]),
            'audio_enabled': bool(result[2]),
            'webcam_enabled': bool(result[3]),
            'novel_algorithms_enabled': bool(result[4]),
            'data_retention_days': result[5],
            'consent_given': bool(result[6]),
            'consent_timestamp': result[7]
        }
    else:
        # Return defaults if no preferences found
        return {
            'ocr_enabled': True,
            'audio_enabled': False,
            'webcam_enabled': False,
            'novel_algorithms_enabled': True,
            'data_retention_days': 30,
            'consent_given': False
        }

# NEW: Track algorithm performance
def log_algorithm_performance(algorithm_name, metric_name, metric_value, sample_size=1):
    """Log algorithm performance metrics"""
    conn = sqlite3.connect(ENHANCED_DB_PATH)
    c = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    
    c.execute("""INSERT INTO algorithm_performance 
                 (algorithm_name, metric_name, metric_value, timestamp, sample_size)
                 VALUES (?, ?, ?, ?, ?)""",
              (algorithm_name, metric_name, metric_value, timestamp, sample_size))
    
    conn.commit()
    conn.close()

# ORIGINAL FUNCTION - PRESERVED (uses original DB)
def log_session(window_title, interaction_rate):
    """ORIGINAL FUNCTION - Log to original database (sessions.db)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ts = datetime.now().isoformat()
    app_name = window_title.split(" - ")[-1] if " - " in window_title else window_title

    c.execute("""INSERT INTO sessions 
                 (start_ts, end_ts, app_name, window_title, interaction_rate) 
                 VALUES (?, ?, ?, ?, ?)""",
              (ts, ts, app_name, window_title, interaction_rate))
    conn.commit()
    conn.close()

# NEW: Initialize both databases
def initialize_all_databases():
    """Initialize both original and enhanced databases"""
    ensure_data_directory()
    init_db()  # Original database
    init_enhanced_db()  # Enhanced database
    logger.info("Both databases initialized successfully")

if __name__ == "__main__":
    initialize_all_databases()
    print("Databases created successfully!")
    print(f"Original database: {DB_PATH}")
    print(f"Enhanced database: {ENHANCED_DB_PATH}")