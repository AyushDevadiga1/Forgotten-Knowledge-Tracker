"""Purge junk tracked_concepts that predate the strengthened ingest gates.

Deletes tracked_concepts that currently fail is_plausible_concept OR are
flagged sensitive, EXCEPT concepts that are linked to the SM-2 deck
(learning_items) or are curated exceptions. Idempotent and safe: backs up the
DB first, keeps deck/graph integrity, and rebuilds the graph cache afterwards.

Usage: python scripts/debug/purge_junk_concepts.py [--dry-run]
"""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tracker_app.config import DB_PATH
from tracker_app.db.models import SessionLocal, TrackedConcept, LearningItem
from tracker_app.learning.concept_promotion import CURATED_EXCEPTIONS
from tracker_app.learning.text_quality_validator import is_plausible_concept
from tracker_app.tracking.privacy_filter import (
    detect_sensitive_data, SENSITIVE_KEYWORD_NOISE,
)


def collect_junk(db) -> list:
    deck = {q for (q,) in db.query(LearningItem.question).all()}
    deck |= set(CURATED_EXCEPTIONS)

    junk = []
    for row in db.query(TrackedConcept).all():
        concept = row.concept
        if concept in deck:
            continue
        bad = not is_plausible_concept(concept)
        sensitive = (
            concept.lower() in SENSITIVE_KEYWORD_NOISE
            or detect_sensitive_data(concept)
        )
        if bad or sensitive:
            junk.append((concept, row.frequency_count, "sensitive" if sensitive else "junk"))
    return junk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be purged without changing anything")
    args = ap.parse_args()

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        sys.exit(1)

    with SessionLocal() as db:
        total = db.query(TrackedConcept).count()
        junk = collect_junk(db)

    print(f"tracked_concepts before: {total}")
    print(f"junk flagged for purge: {len(junk)}")
    for concept, freq, why in sorted(junk, key=lambda x: -x[1]):
        print(f"   {why:<10} {concept!r}  freq={freq}")

    if args.dry_run:
        print("\nDry run — nothing changed.")
        return

    if not junk:
        print("\nNothing to purge.")
        return

    backup = db_path.with_name(f"{db_path.stem}.backup-{datetime.now():%Y%m%d-%H%M%S}{db_path.suffix}")
    shutil.copy2(db_path, backup)
    print(f"\nDB backed up to {backup}")

    names = [c for c, _, _ in junk]
    with SessionLocal() as db:
        for name in names:
            row = db.query(TrackedConcept).filter(TrackedConcept.concept == name).first()
            if row:
                db.delete(row)
        db.commit()

    from tracker_app.tracking.knowledge_graph import (
        _ensure_graph_loaded, get_graph, remove_concept_from_graph,
    )
    _ensure_graph_loaded()
    removed = sum(1 for name in names if remove_concept_from_graph(name))

    with SessionLocal() as db:
        remaining = db.query(TrackedConcept).count()
        dbset = {r.concept for r in db.query(TrackedConcept).all()}
    stale = [n for n in get_graph().nodes if n not in dbset]
    removed_stale = sum(1 for n in stale if remove_concept_from_graph(n))
    print(f"purged {len(names)} concepts ({removed} graph nodes) + "
          f"{removed_stale} stale graph-only nodes, "
          f"tracked_concepts after: {remaining}")


if __name__ == "__main__":
    main()
