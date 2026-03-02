import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

from tracker_app.config import DATA_DIR

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
