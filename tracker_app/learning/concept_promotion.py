"""Promote validated tracked concepts into the SM-2 learning deck.

The Knowledge Base / Review pages read `learning_items`, while passive tracking
writes `tracked_concepts`. This module is the bridge: concepts that survive the
quality gate and show enough repeated exposure become real deck items so the KB
surfaces actual extracted knowledge instead of empty.

Two entry points:
  - `backfill_items()`   one-shot migration of existing tracked concepts
  - `promote_concept_to_deck()` continuous promotion called from ingest
"""

import logging
from typing import Dict, List, Optional

from tracker_app.db.models import SessionLocal, TrackedConcept, ConceptEncounter
from tracker_app.learning.text_quality_validator import is_plausible_concept
from tracker_app.config import DATA_DIR

logger = logging.getLogger("ConceptPromotion")

# Real English words captured from window titles / UI chrome that are never
# study content. Kept OUT of the deck (the graph may still track them).
UI_CHROME = frozenset({
    'explorer', 'context', 'terminal', 'ports', 'code', 'new', 'part',
    'thought', 'fashion', 'round', 'output', 'total', 'problems', 'youtube',
    'device',
})

# Curated phrases the structural gate rejects (odd lettering, function-word
# components) but which are genuinely study topics.
CURATED_EXCEPTIONS_DEFAULT = frozenset({
    'big-o notation',
    'ebbinghaus forgetting curve',
})

_CURATED_EXCEPTIONS_FILE = DATA_DIR / "curated_exceptions.txt"


def _load_curated_exceptions() -> frozenset:
    """Load user-editable curated exceptions from DATA_DIR (L-6).

    Each non-empty line of curated_exceptions.txt is one exception; a line
    starting with '#' is a comment. Falls back to the built-in set when the
    file is missing, cannot be read, or contains no entries.
    """
    try:
        if not _CURATED_EXCEPTIONS_FILE.exists():
            return CURATED_EXCEPTIONS_DEFAULT
        with open(_CURATED_EXCEPTIONS_FILE, encoding="utf-8") as fh:
            entries = {
                line.strip().lower()
                for line in fh
                if line.strip() and not line.lstrip().startswith('#')
            }
        return frozenset(entries) if entries else CURATED_EXCEPTIONS_DEFAULT
    except OSError:
        return CURATED_EXCEPTIONS_DEFAULT


CURATED_EXCEPTIONS = _load_curated_exceptions()

# Auto-promote once a concept has been re-encountered this many times.
PROMOTE_AFTER_ENCOUNTERS = 3
# Backfill lower bound on frequency_count.
MIN_PROMOTION_FREQUENCY = 3


def is_kb_worthy(concept: str) -> bool:
    """Gate for deck promotion: plausible AND not UI chrome."""
    if not concept:
        return False
    c = concept.strip()
    if c in UI_CHROME:
        return False
    if c.lower() in CURATED_EXCEPTIONS:
        return True
    return is_plausible_concept(c)


def _answer_for(db, concept: str) -> str:
    """Build an answer from the most recent meaningful encounter context."""
    enc = (
        db.query(ConceptEncounter)
          .filter(ConceptEncounter.concept == concept)
          .order_by(ConceptEncounter.timestamp.desc())
          .first()
    )
    snippet = (enc.context_snippet or "").strip() if enc else ""
    if snippet.startswith('browser:') and len(snippet) > len('browser:'):
        return f"Captured from your study session on: {snippet[len('browser:'):].strip()}"
    if snippet and snippet != 'ocr' and len(snippet) > 4:
        return f"Captured from your study session: {snippet}"
    return "Automatically tracked from your study sessions — write down what you know about this concept."


def _difficulty_for(relevance_score: Optional[float]) -> str:
    rel = relevance_score or 0.5
    if rel >= 0.7:
        return 'easy'
    if rel >= 0.45:
        return 'medium'
    return 'hard'


def _load_subsuming_phrases() -> frozenset:
    """Preload deck-eligible multi-word concepts for in-memory subsumption.

    Backfill used to issue a leading-wildcard LIKE '%concept%' query per
    candidate -- a full-table scan SQLite can never index. One query up-front
    plus Python set membership replaces it (M-8).
    """
    with SessionLocal() as db:
        rows = db.query(
            TrackedConcept.concept, TrackedConcept.frequency_count
        ).filter(TrackedConcept.concept.like('% %')).all()
    phrases = set()
    for concept, frequency_count in rows:
        if (
            concept and ' ' in concept
            and frequency_count >= MIN_PROMOTION_FREQUENCY
            and is_kb_worthy(concept)
        ):
            phrases.add(concept.strip().lower())
    return frozenset(phrases)


def _is_subsumed_single_word(
    concept: str, subsuming_phrases: Optional[frozenset] = None
) -> bool:
    """A single-word concept already covered by a tracked multi-word phrase
    ('cellular' vs 'cellular respiration') is a fragment, not a concept.
    Only subsumes when the larger phrase is itself deck-eligible, so a concept
    like 'atp' stays promotable when its phrase 'atp energy' is below the
    promotion threshold.

    subsuming_phrases: preloaded frozenset of deck-eligible multi-word
    concepts (M-8). When omitted, falls back to the per-concept DB lookup.
    """
    if ' ' in concept:
        return False
    lc = concept.lower()
    if subsuming_phrases is not None:
        return any(lc in phrase.split() for phrase in subsuming_phrases)
    with SessionLocal() as db:
        others = db.query(TrackedConcept).filter(
            TrackedConcept.concept != concept,
            TrackedConcept.concept.like(f"%{concept}%"),
        ).all()
    for other in others:
        if lc not in other.concept.lower().split():
            continue
        if (
            other.frequency_count >= MIN_PROMOTION_FREQUENCY
            and is_kb_worthy(other.concept)
        ):
            return True
    return False


def promote_concept_to_deck(
    concept: str, subsuming_phrases: Optional[frozenset] = None
) -> Optional[str]:
    """Create a learning item for an extracted concept (idempotent).

    Returns the new item id, or None if the concept already has a deck item
    (matched by exact question) or fails the KB-worthiness gate.
    """
    from tracker_app.learning.learning_tracker import LearningTracker

    if not is_kb_worthy(concept):
        return None
    if _is_subsumed_single_word(concept, subsuming_phrases=subsuming_phrases):
        logger.debug(f"Fragment of a larger concept, not promoting: {concept!r}")
        return None

    with SessionLocal() as db:
        # Exact-match idempotency check against the deck.
        from tracker_app.db.models import LearningItem
        dup = db.query(LearningItem).filter(LearningItem.question == concept).first()
        if dup:
            logger.debug(f"Already in deck: {concept!r}")
            return None
        tc = db.query(TrackedConcept).filter(TrackedConcept.concept == concept).first()
        answer = _answer_for(db, concept)

    item_id = LearningTracker().add_learning_item(
        question=concept,
        answer=answer,
        difficulty=_difficulty_for(tc.relevance_score if tc else None),
        item_type='concept',
        tags=['extracted'],
    )
    logger.info(f"Promoted extracted concept to deck: {concept!r} -> {item_id}")
    return item_id


def backfill_items(
    min_frequency: int = MIN_PROMOTION_FREQUENCY,
    limit: Optional[int] = None,
) -> Dict:
    """One-shot migration of existing tracked concepts into the deck.

    Selects concepts with enough encounters, ordered by frequency then recency,
    and promotes every KB-worthy one. Safe to re-run: existing questions are
    skipped.
    """
    with SessionLocal() as db:
        q = (
            db.query(TrackedConcept)
              .filter(TrackedConcept.frequency_count >= min_frequency)
              .order_by(
                  TrackedConcept.frequency_count.desc(),
                  TrackedConcept.last_seen.desc(),
              )
        )
        if limit:
            q = q.limit(limit)
        candidates = [r.concept for r in q.all()]

    subsuming_phrases = _load_subsuming_phrases()
    promoted: List[str] = []
    skipped: List[str] = []
    for concept in candidates:
        if not is_kb_worthy(concept):
            skipped.append(concept)
            continue
        item_id = promote_concept_to_deck(
            concept, subsuming_phrases=subsuming_phrases
        )
        (promoted if item_id else skipped).append(concept)

    return {
        'promoted': promoted,
        'skipped': skipped,
        'promoted_count': len(promoted),
        'skipped_count': len(skipped),
        'min_frequency': min_frequency,
    }
