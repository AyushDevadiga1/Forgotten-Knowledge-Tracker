"""SM-2 concept scheduling with AWFC-personalised decay (lambda per concept)."""

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

    # ΓöÇΓöÇ Add / update a concept ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    def add_concept(
        self,
        concept: str,
        confidence: float = 0.5,
        context: str = "",
        attention_at_encoding: float = 50.0,
    ) -> str:
        """
        Insert or update a tracked concept.
        Stores attention_at_encoding for AWFC ╬╗ personalisation.
        Returns the concept string (primary key), or None if the concept
        is rejected by the plausibility filter (OCR noise, word fragments).
        """
        from tracker_app.learning.memory_model import compute_awfc_lambda
        from tracker_app.learning.text_quality_validator import is_plausible_concept

        if not is_plausible_concept(concept):
            logger.debug("Skipping implausible concept: %r", concept)
            return None

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

        # Keep the in-memory knowledge graph in step with the live SM-2/AWFC
        # row (Phase 11.2) — a re-encounter resets the retention clock.
        try:
            from tracker_app.tracking.knowledge_graph import sync_concept_to_graph
            sync_concept_to_graph(concept)
        except Exception as e:
            logger.debug(f"Graph sync skipped for {concept}: {e}")

        return concept

    # ΓöÇΓöÇ SM-2 review scheduling ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    def schedule_next_review(self, concept_id: str, quality: int = 3):
        """
        Schedule next review using standard SM-2 shared with sm2_memory_model,
        plus AWFC-personalised λ.
        concept_id = concept string (PK), not an integer.
        quality: 0–5 (0=fail, 5=perfect recall).
        """
        from tracker_app.learning.sm2_memory_model import (
            MIN_EASE_FACTOR, MAX_EASE_FACTOR, QUALITY_THRESHOLD,
            SECOND_REVIEW_INTERVAL_DAYS,
        )
        with models.SessionLocal() as db:
            tracked = (db.query(TrackedConcept)
                         .filter(TrackedConcept.concept == concept_id)
                         .first())

            if not tracked:
                logger.warning(f"schedule_next_review: '{concept_id}' not found.")
                return

            interval    = getattr(tracked, "interval", 1) or 1
            ease        = getattr(tracked, "memory_strength", 2.5) or 2.5
            repetitions = getattr(tracked, "repetitions", 0) or 0

            # Ease factor adjusts on every review (success AND failure) using
            # the canonical SM-2 formula — the tested implementation applies it
            # unconditionally, so we do too instead of the old flat -0.2.
            delta      = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
            new_ease   = max(MIN_EASE_FACTOR, min(ease + delta, MAX_EASE_FACTOR))

            if quality < QUALITY_THRESHOLD:
                # Failed — reset to first repetition, re-review tomorrow.
                repetitions = 1
                new_interval = 1
            else:
                repetitions += 1
                if repetitions == 1:
                    new_interval = 1
                elif repetitions == 2:
                    new_interval = SECOND_REVIEW_INTERVAL_DAYS
                else:
                    new_interval = max(1, round(interval * new_ease))

            tracked.interval        = new_interval
            tracked.memory_strength = new_ease
            tracked.repetitions     = repetitions
            tracked.next_review     = datetime.utcnow() + timedelta(days=new_interval)
            # A review is a reinforcement event: reset the retention clock so
            # the AWFC memory score (and the graph's live copy) reflect the
            # fresh recall rather than the last OCR encounter.
            tracked.last_seen       = datetime.utcnow()

            # Optionally recalibrate ╬╗ after enough reviews
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
                    logger.debug(f"╬╗ recalibration skipped: {e}")

            db.commit()
            logger.debug(f"Scheduled '{concept_id}' in {new_interval}d "
                         f"(quality={quality}, ╬╗={tracked.lambda_personalised:.4f})")

            # Reflect the fresh review in the knowledge graph (Phase 11.2).
            try:
                from tracker_app.tracking.knowledge_graph import sync_concept_to_graph
                sync_concept_to_graph(concept_id)
            except Exception as e:
                logger.debug(f"Graph sync skipped for {concept_id}: {e}")

    # ΓöÇΓöÇ Get due concepts ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

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

    # ΓöÇΓöÇ Concept history ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

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
