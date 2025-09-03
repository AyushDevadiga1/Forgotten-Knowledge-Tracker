import sqlite3
import json
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="data/tracking.db"):
        self.db_path = db_path
        # Ensure data directory exists - handle both relative and absolute paths
        db_dir = os.path.dirname(db_path)
        if db_dir:  # Only create directory if path contains a directory
            os.makedirs(db_dir, exist_ok=True)
        self.initialize_database()
    
    def execute_query(self, query, params=(), fetch_results=False):
        """Execute a SQL query with parameters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch_results:
                results = cursor.fetchall()
                conn.close()
                return results
            else:
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return False if not fetch_results else []
    
    def initialize_database(self):
        """Create all necessary tables if they don't exist"""
        # Window tracking table (existing)
        window_table = """
        CREATE TABLE IF NOT EXISTS window_history (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            app TEXT NOT NULL,
            start_time TEXT NOT NULL,
            duration INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # Screenshots table (new)
        screenshots_table = """
        CREATE TABLE IF NOT EXISTS screenshots (
            id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            window_title TEXT,
            app_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # OCR results table (new)
        ocr_table = """
        CREATE TABLE IF NOT EXISTS ocr_results (
            id INTEGER PRIMARY KEY,
            screenshot_id INTEGER,
            extracted_text TEXT,
            confidence REAL,
            word_count INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (screenshot_id) REFERENCES screenshots (id)
        )
        """
        
        self.execute_query(window_table)
        self.execute_query(screenshots_table)
        self.execute_query(ocr_table)
    
    def save_screenshot(self, file_path, timestamp, window_title, app_name):
        """Save screenshot metadata to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            INSERT INTO screenshots (file_path, timestamp, window_title, app_name)
            VALUES (?, ?, ?, ?)
            """, (file_path, timestamp, window_title, app_name))
            
            screenshot_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.debug(f"Screenshot saved with ID: {screenshot_id}")
            return screenshot_id
            
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            return None

    def save_ocr_result(self, screenshot_id, extracted_text, confidence, word_count):
        """Save OCR results to database"""
        query = """
        INSERT INTO ocr_results (screenshot_id, extracted_text, confidence, word_count)
        VALUES (?, ?, ?, ?)
        """
        return self.execute_query(query, (screenshot_id, extracted_text, confidence, word_count))
    
    def save_window_entry(self, entry):
        """Save a window tracking entry to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO window_history (title, app, start_time, duration)
            VALUES (?, ?, ?, ?)
            ''', (entry['title'], entry['app'], entry['timestamp'], entry['duration']))
            
            conn.commit()
            conn.close()
            logger.debug(f"Saved window entry: {entry['app']} - {entry['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            return False
    
    def get_recent_history(self, limit=50):
        """Get recent tracking history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT title, app, start_time, duration 
            FROM window_history 
            ORDER BY start_time DESC 
            LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [{
                'title': row[0],
                'app': row[1],
                'timestamp': row[2],
                'duration': row[3]
            } for row in results]
            
        except Exception as e:
            logger.error(f"Error reading from database: {e}")
            return []
    
    def get_total_tracking_time(self):
        """Get total tracking time from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT SUM(duration) FROM window_history')
            total_time = cursor.fetchone()[0] or 0
            conn.close()
            
            return total_time
            
        except Exception as e:
            logger.error(f"Error getting total tracking time: {e}")
            return 0
    
    def get_most_used_apps(self, limit=10):
        """Get most frequently used applications"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT app, SUM(duration) as total_time, COUNT(*) as usage_count
            FROM window_history 
            GROUP BY app 
            ORDER BY total_time DESC 
            LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [{
                'app': row[0],
                'total_time': row[1],
                'usage_count': row[2]
            } for row in results]
            
        except Exception as e:
            logger.error(f"Error getting most used apps: {e}")
            return []
    
    def clear_database(self):
        """Clear all data from database (for testing)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM window_history')
            cursor.execute('DELETE FROM screenshots')
            cursor.execute('DELETE FROM ocr_results')
            
            conn.commit()
            conn.close()
            logger.info("Database cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            return False
    
    def get_screenshot_count(self):
        """Get total number of screenshots"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM screenshots')
            count = cursor.fetchone()[0] or 0
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting screenshot count: {e}")
            return 0
    
    def get_ocr_result_count(self):
        """Get total number of OCR results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM ocr_results')
            count = cursor.fetchone()[0] or 0
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting OCR result count: {e}")
            return 0