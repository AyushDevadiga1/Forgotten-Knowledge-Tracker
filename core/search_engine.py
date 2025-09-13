import sqlite3
import re
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class KnowledgeSearch:
    def __init__(self, db_path="data/tracking.db"):
        self.db_path = db_path
        logger.info(f"Knowledge search initialized with database: {db_path}")
    
    def search_all(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search across all knowledge sources: windows, screenshots, audio
        Returns combined results sorted by relevance
        """
        if not query or not query.strip():
            return []
            
        query = query.strip()
        logger.info(f"🔍 Searching for: '{query}'")
        
        results = []
        
        # Search window history
        window_results = self._search_windows(query, limit)
        results.extend(window_results)
        
        # Search OCR text from screenshots  
        ocr_results = self._search_ocr(query, limit)
        results.extend(ocr_results)
        
        # Search audio transcripts
        audio_results = self._search_audio(query, limit)
        results.extend(audio_results)
        
        # Sort by relevance score (highest first) then timestamp (newest first)
        results.sort(key=lambda x: (-x['relevance'], x['timestamp']), reverse=True)
        
        logger.info(f"✅ Found {len(results)} results for '{query}'")
        return results[:limit]
    
    def _search_windows(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search window titles and applications"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT title, app, start_time, duration 
                FROM window_history 
                WHERE title LIKE ? OR app LIKE ?
                ORDER BY start_time DESC 
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))
            
            results = []
            for title, app, start_time, duration in cursor.fetchall():
                result_text = f"{title} ({app})"
                relevance = self._calculate_relevance(result_text, query)
                
                results.append({
                    'type': 'window_activity',
                    'source': 'Window Tracking',
                    'title': title,
                    'app': app,
                    'timestamp': start_time,
                    'duration': duration,
                    'relevance': relevance,
                    'snippet': self._highlight_text(result_text, query),
                    'content': result_text
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Window search error: {e}")
            return []
    
    def _search_ocr(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search OCR text from screenshots"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.file_path, s.timestamp, s.window_title, o.extracted_text, o.confidence
                FROM ocr_results o
                JOIN screenshots s ON o.screenshot_id = s.id
                WHERE o.extracted_text LIKE ?
                ORDER BY s.timestamp DESC 
                LIMIT ?
            ''', (f'%{query}%', limit))
            
            results = []
            for file_path, timestamp, window_title, text, confidence in cursor.fetchall():
                relevance = self._calculate_relevance(text, query)
                
                results.append({
                    'type': 'screenshot',
                    'source': 'Screenshot OCR',
                    'file_path': file_path,
                    'timestamp': timestamp,
                    'window_title': window_title,
                    'confidence': confidence,
                    'relevance': relevance,
                    'snippet': self._highlight_text(self._truncate_text(text, 150), query),
                    'content': text
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"OCR search error: {e}")
            return []
    
    def _search_audio(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search audio transcripts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT file_path, timestamp, transcribed_text, confidence, duration
                FROM audio_recordings 
                WHERE transcribed_text LIKE ?
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (f'%{query}%', limit))
            
            results = []
            for file_path, timestamp, transcribed_text, confidence, duration in cursor.fetchall():
                relevance = self._calculate_relevance(transcribed_text, query)
                
                results.append({
                    'type': 'audio',
                    'source': 'Audio Recording',
                    'file_path': file_path,
                    'timestamp': timestamp,
                    'duration': duration,
                    'confidence': confidence,
                    'relevance': relevance,
                    'snippet': self._highlight_text(self._truncate_text(transcribed_text, 150), query),
                    'content': transcribed_text
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Audio search error: {e}")
            return []
    
    def _calculate_relevance(self, text: str, query: str) -> float:
        """Calculate relevance score between 0-100"""
        if not text or not query:
            return 0.0
            
        text_lower = text.lower()
        query_lower = query.lower()
        
        # Frequency of query terms
        term_count = text_lower.count(query_lower)
        relevance = min(term_count * 30, 100)  # Cap at 100
        
        # Boost if at beginning of text
        if text_lower.startswith(query_lower):
            relevance += 20
            
        # Boost for exact matches
        if query_lower in text_lower:
            relevance += 15
            
        return min(relevance, 100)
    
    def _highlight_text(self, text: str, query: str) -> str:
        """Highlight search terms in text with Markdown-style formatting"""
        if not text or not query:
            return text
            
        try:
            # Use regex for case-insensitive highlighting
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            return pattern.sub(r'**\g<0>**', text)
        except:
            return text
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text with ellipsis if too long"""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(' ', 1)[0] + '...'
    
    def get_recent_activity(self, hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent activity across all sources"""
        try:
            # This would combine recent items from all tables
            # Implementation would be similar to search but without query filtering
            return []
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return []

# Singleton instance for easy access
knowledge_search = KnowledgeSearch()