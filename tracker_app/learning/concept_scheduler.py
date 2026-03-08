import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import uuid

from tracker_app.config import DATA_DIR
from tracker_app.db.models import TrackedConcept, ConceptEncounter, SessionLocal
from sqlalchemy.orm import Session

class ConceptScheduler:
    """SM-2 inspired scheduling for tracked concepts using SQLAlchemy"""
    
    def __init__(self, db_path: str = None):
        # We rely on the unified SessionLocal schema now.
        pass
    
    def _init_db(self):
        """Legacy initialization. Unused as base metadata creates structure globally."""
        pass
    
    def add_concept(self, concept: str, confidence: float = 0.5, context: str = "") -> str:
        """Add or update a tracked concept"""
        now = datetime.now().isoformat()
        
        with SessionLocal() as db:
            existing = db.query(TrackedConcept).filter(TrackedConcept.concept == concept).first()
            if existing:
                concept_id = existing.concept
                existing.last_seen = now
                existing.frequency_count += 1
                existing.relevance_score = (existing.relevance_score + confidence) / 2.0
            else:
                concept_id = concept
                new_concept = TrackedConcept(
                    concept=concept,
                    first_seen=now,
                    last_seen=now,
                    next_review=now,
                    relevance_score=confidence
                )
                db.add(new_concept)
            
            encounter = ConceptEncounter(
                concept=concept_id, # Wait, model says "concept" but DB had "concept_id". The model says: concept = Column(String, index=True)
                timestamp=now,
                source="ui", # Added source because model schema has it
                confidence=confidence,
                context_snippet=context # model has context_snippet instead of context
            )
            db.add(encounter)
            db.commit()
            
        return concept_id
    
    def schedule_next_review(self, concept_id: str, quality: int = 3):
        """
        Schedule next review using SM-2 algorithm
        quality: 0-5 (0=fail, 5=perfect)
        """
        with SessionLocal() as db:
            tracked = db.query(TrackedConcept).filter(TrackedConcept.id == concept_id).first()
            
            if not tracked:
                return
            
            # Need to adapt because model uses `memory_strength` and `relevance_score` but no `sm2_interval` or `sm2_ease`
            # Actually, `models.py` only defines TrackedConcept with fields:
            # id, concept, first_seen, last_seen, encounter_count, relevance_score, memory_strength, next_review, context, related_concepts
            # I must dynamically manage interval/ease within the object if it's missing, but the old one had it.
            # I will use a simple heuristic for next review interval based on memory_strength.
            
            interval = getattr(tracked, 'interval', 1) 
            ease = getattr(tracked, 'memory_strength', 2.5)
            
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
            
            tracked.interval = new_interval
            tracked.memory_strength = new_ease
            tracked.next_review = (datetime.now() + timedelta(days=new_interval)).isoformat()
            
            db.commit()
    
    def get_due_concepts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get concepts due for review"""
        now = datetime.now().isoformat() 
        
        with SessionLocal() as db:
            concepts = db.query(TrackedConcept).filter(
                TrackedConcept.next_review <= now
            ).order_by(TrackedConcept.relevance_score.desc(), TrackedConcept.next_review.asc()).limit(limit).all()
            
            return [
                {
                    'id': c.concept,
                    'concept': c.concept,
                    'encounter_count': c.frequency_count,
                    'interval': getattr(c, 'interval', 1),
                    'relevance': c.relevance_score
                }
                for c in concepts
            ]
    
    def get_concept_history(self, concept: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get encounter history for a concept"""
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with SessionLocal() as db:
            # Fetch TC ID first
            tc = db.query(TrackedConcept).filter(TrackedConcept.concept == concept).first()
            if not tc:
                return []
                
            encounters = db.query(ConceptEncounter).filter(
                ConceptEncounter.concept == tc.concept,
                ConceptEncounter.timestamp >= start_date
            ).order_by(ConceptEncounter.timestamp.desc()).all()
            
            return [
                {
                    'timestamp': e.timestamp,
                    'context': e.context_snippet,
                    'confidence': e.confidence,
                    'relevance': tc.relevance_score
                }
                for e in encounters
            ]

if __name__ == "__main__":
    from tracker_app.db.db_module import init_all_databases
    init_all_databases()
    scheduler = ConceptScheduler()
    c_id = scheduler.add_concept("Docker Compose", 0.9, "Learned about multi-stage builds")
    print(f"Added concept with ID: {c_id}")
    due = scheduler.get_due_concepts()
    print(f"Due Concepts: {len(due)}")
