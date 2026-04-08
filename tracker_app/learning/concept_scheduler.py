# learning/concept_scheduler.py — FKT 2.0 Phase 4
# SM-2 scheduling with AWFC (Attention-Weighted Forgetting Curve).
# Passes attention_at_encoding when saving concepts so λ is personalised
# per concept from the first encounter.

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from tracker_app.config import DATA_DIR, DEFAULT_LAMBDA
from tracker_app.db import models
from tracker_app.db.models import TrackedConcept, ConceptEncounter, SessionLocal

logger = logging.getLogger("ConceptScheduler")


class ConceptScheduler:
    """SM-2 + AWFC scheduling for auto-tracked concepts."""

    def __init__(self, db_path: str = None):
        pass  # SessionLocal is the shared singleton

    # ── Add / update a concept ───────────────────────────────────────────────

    def add_concept(
        self,
        concept: str,
        confidence: float = 0.5,
        context: str = "",
        attention_at_encoding: float = 50.0,
    ) -> str:
        """
        Insert or update a tracked concept.
        Stores attention_at_encoding for AWFC λ personalisation.
        Returns the concept string (primary key).
        """
        from tracker_app.learning.memory_model import compute_awfc_lambda

        now = datetime.utcnow()

        with SessionLocal() as db:
            existing = (db.query(TrackedConcept)
                          .filter(TrackedConcept.concept == concept)
                          .first())

            if existing:
                # Rolling average of attention at encoding (EMA 80/20)
                existing.attention_at_encoding = (
                    0.8 * (existing.attention_at_encoding or 50.0)
                    + 0.2 * attention_at_encoding
                )
                existing.lambda_personalised = compute_awfc_lambda(
                    DEFAULT_LAMBDA, existing.attention_at_encoding
                )
                existing.last_seen       = now
                existing.frequency_count = (existing.frequency_count or 0) + 1
                existing.relevance_score = (
                    ((existing.relevance_score or 0.5) + confidence) / 2.0
                )
            else:
                lambda_p = compute_awfc_lambda(DEFAULT_LAMBDA, attention_at_encoding)
                new_concept = TrackedConcept(
                    concept=concept,
                    first_seen=now,
                    last_seen=now,
                    next_review=now,
                    relevance_score=confidence,
                    attention_at_encoding=attention_at_encoding,
                    lambda_personalised=lambda_p,
                )
                db.add(new_concept)

            encounter = ConceptEncounter(
                concept=concept,
                timestamp=now,
                source="ocr",
                confidence=confidence,
                context_snippet=context[:200] if context else "",
            )
            db.add(encounter)
            db.commit()

        return concept

    # ── SM-2 review scheduling ───────────────────────────────────────────────

    def schedule_next_review(self, concept_id: str, quality: int = 3):
        """
        Schedule next review using SM-2 + AWFC-personalised λ.
        concept_id = concept string (PK), not an integer.
        quality: 0–5 (0=fail, 5=perfect recall).
        """
        with models.SessionLocal() as db:
            tracked = (db.query(TrackedConcept)
                         .filter(TrackedConcept.concept == concept_id)
                         .first())

            if not tracked:
                logger.warning(f"schedule_next_review: '{concept_id}' not found.")
                return

            interval = getattr(tracked, "interval", 1) or 1
            ease     = getattr(tracked, "memory_strength", 2.5) or 2.5

            if quality < 3:
                new_interval = 1
                new_ease     = max(1.3, ease - 0.2)
            else:
                new_interval = 3 if interval <= 1 else round(interval * ease)
                delta        = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
                new_ease     = max(1.3, min(ease + delta, 3.5))

            tracked.interval        = new_interval
            tracked.memory_strength = new_ease
            tracked.next_review     = datetime.utcnow() + timedelta(days=new_interval)

            # Optionally recalibrate λ after enough reviews
            total = tracked.frequency_count or 0
            if total >= 5:
                try:
                    from tracker_app.learning.memory_model import recalibrate_lambda
                    correct_rate = (quality / 5.0)  # approximate from single rating
                    tracked.lambda_personalised = recalibrate_lambda(
                        concept_id,
                        tracked.lambda_personalised or DEFAULT_LAMBDA,
                        actual_success_rate=correct_rate,
                        n_reviews=total,
                        first_seen=tracked.first_seen,
                    )
                except Exception as e:
                    logger.debug(f"λ recalibration skipped: {e}")

            db.commit()
            logger.debug(f"Scheduled '{concept_id}' in {new_interval}d "
                         f"(quality={quality}, λ={tracked.lambda_personalised:.4f})")

    # ── Get due concepts ─────────────────────────────────────────────────────

    def get_due_concepts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return concepts whose next_review is now or overdue."""
        now = datetime.utcnow()

        with models.SessionLocal() as db:
            concepts = (
                db.query(TrackedConcept)
                  .filter(TrackedConcept.next_review <= now)
                  .order_by(
                      TrackedConcept.relevance_score.desc(),
                      TrackedConcept.next_review.asc(),
                  )
                  .limit(limit)
                  .all()
            )

            return [
                {
                    "id":                   c.concept,
                    "concept":              c.concept,
                    "encounter_count":      c.frequency_count,
                    "interval":             getattr(c, "interval", 1),
                    "relevance":            c.relevance_score,
                    "attention_at_encoding": getattr(c, "attention_at_encoding", 50.0),
                    "lambda_personalised":  getattr(c, "lambda_personalised", DEFAULT_LAMBDA),
                }
                for c in concepts
            ]

    # ── Concept history ──────────────────────────────────────────────────────

    def get_concept_history(
        self, concept: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Encounter history for a concept over the last N days."""
        start = datetime.utcnow() - timedelta(days=days)

        with models.SessionLocal() as db:
            tc = (db.query(TrackedConcept)
                    .filter(TrackedConcept.concept == concept)
                    .first())
            if not tc:
                return []

            encounters = (
                db.query(ConceptEncounter)
                  .filter(
                      ConceptEncounter.concept == tc.concept,
                      ConceptEncounter.timestamp >= start,
                  )
                  .order_by(ConceptEncounter.timestamp.desc())
                  .all()
            )

            return [
                {
                    "timestamp":  e.timestamp.isoformat() if isinstance(e.timestamp, datetime)
                                  else str(e.timestamp),
                    "context":    e.context_snippet,
                    "confidence": e.confidence,
                    "relevance":  tc.relevance_score,
                }
                for e in encounters
            ]


if __name__ == "__main__":
    from tracker_app.db.db_module import init_all_databases
    init_all_databases()
    s  = ConceptScheduler()
    cid = s.add_concept("backpropagation", 0.85,
                        "studying neural networks", attention_at_encoding=78)
    print(f"Added: {cid}")
    due = s.get_due_concepts()
    print(f"Due: {len(due)}")
