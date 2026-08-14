"""Tests: TrackedConcept SM-2 scheduling (Phase 11.6).

The auto-tracked concept system previously re-implemented SM-2 off
`interval <= 1`, which skipped the canonical 1-day initial-reinforcement step
and applied a flat ease penalty on failure. It now tracks `repetitions` and
shares the same constants/formulas as the tested sm2_memory_model.SM2Scheduler.

Run: python -m pytest tracker_app/tests/test_concept_scheduler.py -v
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tracker_app.db import models
from tracker_app.db.models import Base, TrackedConcept
from tracker_app.learning.concept_scheduler import ConceptScheduler


@pytest.fixture
def db(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "SessionLocal", TestingSessionLocal)
    # add_concept uses the SessionLocal bound at import time in
    # concept_scheduler, not models.SessionLocal attribute lookup.
    monkeypatch.setattr(
        "tracker_app.learning.concept_scheduler.SessionLocal",
        TestingSessionLocal,
    )
    return TestingSessionLocal


@pytest.fixture
def scheduler(db):
    with db() as session:
        session.add(TrackedConcept(concept="backpropagation"))
        session.commit()
    return ConceptScheduler()


def _row(db, concept="backpropagation"):
    from tracker_app.db.models import TrackedConcept as TC
    with db() as session:
        return session.query(TC).filter(TC.concept == concept).first()


def test_first_success_gives_1_day(db, scheduler):
    scheduler.schedule_next_review("backpropagation", quality=5)
    row = _row(db)
    assert row.interval == 1
    assert row.repetitions == 1


def test_second_success_gives_3_days(db, scheduler):
    scheduler.schedule_next_review("backpropagation", quality=5)
    scheduler.schedule_next_review("backpropagation", quality=5)
    row = _row(db)
    assert row.interval == 3
    assert row.repetitions == 2


def test_third_success_uses_ease_factor(db, scheduler):
    scheduler.schedule_next_review("backpropagation", quality=5)  # rep 1, int 1
    scheduler.schedule_next_review("backpropagation", quality=5)  # rep 2, int 3
    scheduler.schedule_next_review("backpropagation", quality=5)  # rep 3
    row = _row(db)
    # round(3 * new_ease); new_ease = min(3.5, 2.5 + 0.1) = 2.6 -> 8
    assert row.repetitions == 3
    assert row.interval == round(3 * 2.6)


def test_failure_resets_repetitions_and_interval(db, scheduler):
    scheduler.schedule_next_review("backpropagation", quality=5)
    scheduler.schedule_next_review("backpropagation", quality=5)
    scheduler.schedule_next_review("backpropagation", quality=1)
    row = _row(db)
    assert row.interval == 1
    assert row.repetitions == 1


def test_failure_decreases_ease_factor(db, scheduler):
    scheduler.schedule_next_review("backpropagation", quality=0)
    row = _row(db)
    assert row.memory_strength < 2.5  # canonical SM-2 penalty, not flat -0.2


def test_ease_factor_stays_above_minimum(db, scheduler):
    scheduler.schedule_next_review("backpropagation", quality=0)
    scheduler.schedule_next_review("backpropagation", quality=0)
    row = _row(db)
    assert row.memory_strength >= 1.3


@pytest.fixture
def no_graph_sync(monkeypatch):
    monkeypatch.setattr(
        "tracker_app.tracking.knowledge_graph.sync_concept_to_graph",
        lambda concept: None,
    )


def test_reexposure_recomputes_lambda_before_any_reviews(db, scheduler, no_graph_sync):
    # repetitions == 0: nothing personalised to protect, so a re-encounter
    # still fully recomputes lambda from the fresh attention EMA.
    from tracker_app.config import DEFAULT_LAMBDA
    from tracker_app.learning.memory_model import compute_awfc_lambda

    scheduler.add_concept("backpropagation", attention_at_encoding=90.0)
    row = _row(db)
    # EMA: 0.8*50 (default) + 0.2*90 = 58
    expected = compute_awfc_lambda(DEFAULT_LAMBDA, 58.0)
    assert abs(row.lambda_personalised - expected) < 1e-9


def test_reexposure_nudges_not_overwrites_lambda_after_reviews(db, scheduler, no_graph_sync):
    # Once reviews exist (repetitions > 0) lambda may have been recalibrated
    # from real recall. A passive OCR re-encounter must nudge toward the
    # attention-based estimate, not replace the personalised value.
    from tracker_app.config import DEFAULT_LAMBDA
    from tracker_app.learning.memory_model import compute_awfc_lambda

    scheduler.schedule_next_review("backpropagation", quality=5)
    with db() as session:
        row = session.query(TrackedConcept).filter(
            TrackedConcept.concept == "backpropagation"
        ).first()
        row.lambda_personalised = 0.42  # simulate recalibrated personalisation
        session.commit()

    scheduler.add_concept("backpropagation", attention_at_encoding=90.0)
    row = _row(db)
    attention_lambda = compute_awfc_lambda(DEFAULT_LAMBDA, 58.0)
    expected = 0.9 * 0.42 + 0.1 * attention_lambda
    assert row.lambda_personalised != 0.42
    assert abs(row.lambda_personalised - expected) < 1e-9


def test_matches_tested_sm2_scheduler_across_quality_sequence(db, scheduler, no_graph_sync):
    # H-1 verification: concept_scheduler must produce the SAME interval,
    # ease, and repetition results as the tested SM2Scheduler for any review
    # sequence, not just the happy path. Drive both through a mixed sequence
    # (successes and failures) and compare after every single step.
    from tracker_app.learning.sm2_memory_model import SM2Item, SM2Scheduler

    item = SM2Item(item_id="probe", question="?", answer=".")

    sequence = [5, 5, 5, 2, 5, 4, 0, 5, 3, 1]
    for quality in sequence:
        result = SM2Scheduler.calculate_next_interval(item, quality)
        scheduler.schedule_next_review("backpropagation", quality=quality)
        row = _row(db)

        assert row.interval == result["next_interval_days"]
        assert row.repetitions == result["repetitions"]
        assert abs(row.memory_strength - result["ease_factor"]) < 1e-9


def test_review_counters_track_quizzes(db, scheduler, no_graph_sync):
    # M-6: every schedule_next_review call is one quiz review. Verify the
    # cumulative counters that feed recalibration.
    scheduler.schedule_next_review("backpropagation", quality=5)
    scheduler.schedule_next_review("backpropagation", quality=5)
    scheduler.schedule_next_review("backpropagation", quality=2)
    row = _row(db)
    assert row.review_count == 3
    assert row.correct_count == 2


def test_recalibration_waits_for_five_reviews(db, scheduler, no_graph_sync):
    # M-6: no lambda recalibration before 5 quiz reviews, no matter how many
    # OCR re-encounters the concept had.
    from tracker_app.config import DEFAULT_LAMBDA

    with db() as session:
        row = session.query(TrackedConcept).filter(
            TrackedConcept.concept == "backpropagation"
        ).first()
        row.lambda_personalised = 0.42
        row.frequency_count = 99  # old proxy must NOT trigger recalibration
        session.commit()

    for _ in range(4):
        scheduler.schedule_next_review("backpropagation", quality=5)

    row = _row(db)
    assert row.review_count == 4
    assert abs(row.lambda_personalised - 0.42) < 1e-12


def test_recalibration_uses_cumulative_success_rate(db, scheduler, no_graph_sync):
    # M-6: at the 5th review, lambda must be recalibrated from the CUMULATIVE
    # success rate (4/5), not the last review's single rating (quality 2 -> 0.4).
    from datetime import datetime, timedelta
    import math

    first_seen = datetime.utcnow() - timedelta(days=2)
    with db() as session:
        row = session.query(TrackedConcept).filter(
            TrackedConcept.concept == "backpropagation"
        ).first()
        row.first_seen = first_seen
        row.lambda_personalised = 0.1
        session.commit()

    for _ in range(4):
        scheduler.schedule_next_review("backpropagation", quality=5)
    scheduler.schedule_next_review("backpropagation", quality=2)

    row = _row(db)
    t_hours = (datetime.utcnow() - row.first_seen).total_seconds() / 3600.0
    predicted = math.exp(-0.1 * t_hours)  # predicted at recalibration time (λ was 0.1)

    # Recompute with the corrected inputs to prove what was passed: n=5,
    # actual_success_rate = correct_count/review_count = 4/5, NOT quality/5.
    assert row.review_count == 5
    assert row.correct_count == 4
    expected = 0.1 + 0.05 * (predicted - 0.8)
    assert abs(row.lambda_personalised - expected) < 1e-6
    # And the old buggy value (quality/5 = 0.4) would have produced a
    # measurably different lambda than (4/5 = 0.8).
    buggy = 0.1 + 0.05 * (predicted - 0.4)
    assert abs(row.lambda_personalised - buggy) > 1e-3


def test_reexposure_auto_promotes_to_deck_at_threshold(db, monkeypatch, no_graph_sync):
    # Phase 12: a concept re-encountered enough times is auto-promoted into
    # the learning deck (the KB surface). Uses the same in-memory SessionLocal
    # so the promotion write lands in the test DB, and only promotes once.
    from tracker_app.db.models import LearningItem
    from tracker_app.learning.concept_promotion import PROMOTE_AFTER_ENCOUNTERS
    from tracker_app.learning import concept_promotion as cp
    monkeypatch.setattr(cp, "SessionLocal", db)

    scheduler = ConceptScheduler()
    for _ in range(PROMOTE_AFTER_ENCOUNTERS):
        scheduler.add_concept("hash table", confidence=0.5, context="browser:Notes")

    with db() as session:
        tc = session.query(TrackedConcept).filter(
            TrackedConcept.concept == "hash table"
        ).first()
        assert tc.frequency_count == PROMOTE_AFTER_ENCOUNTERS
        assert session.query(LearningItem).filter(
            LearningItem.question == "hash table"
        ).count() == 1

    # A 4th encounter must not create a duplicate deck item.
    scheduler.add_concept("hash table", confidence=0.5, context="browser:Notes")
    with db() as session:
        assert session.query(LearningItem).filter(
            LearningItem.question == "hash table"
        ).count() == 1


def test_reexposure_does_not_promote_noise(db, monkeypatch, no_graph_sync):
    # UI chrome / OCR noise reaches the tracked_concepts gate on re-encounter,
    # but never enters the learning deck.
    from tracker_app.db.models import LearningItem
    from tracker_app.learning import concept_promotion as cp
    monkeypatch.setattr(cp, "SessionLocal", db)

    scheduler = ConceptScheduler()
    for _ in range(5):
        scheduler.add_concept("explorer", confidence=0.5, context="ocr")

    with db() as session:
        assert session.query(LearningItem).count() == 0


def test_add_concept_rejects_marker_noise_words(db, no_graph_sync):
    # Defense-in-depth: even a direct add_concept call must never persist
    # redaction-marker noise ('password', 'email', 'field') as concepts.
    scheduler = ConceptScheduler()
    for word in ("password", "email", "field", "redacted", "phone", "ssn"):
        assert scheduler.add_concept(word, confidence=0.9, context="ocr") is None, word


def test_add_concept_rejects_pii_patterns(db, no_graph_sync):
    # PII that slips past the pipeline redactor must still be blocked here.
    scheduler = ConceptScheduler()
    for bad in ("john.doe@example.com", "123-45-6789", "555-867-5309",
                "4111-1111-1111-1111"):
        assert scheduler.add_concept(bad, confidence=0.9, context="ocr") is None, bad


def test_add_concept_rejects_ocr_fragments(db, no_graph_sync):
    # Suffix fragments and 3-letter junk must never become tracked concepts.
    scheduler = ConceptScheduler()
    for junk in ("ase", "res", "deapof", "ybpteess", "cobiecfeevhp"):
        assert scheduler.add_concept(junk, confidence=0.9, context="ocr") is None, junk


def test_add_concept_keeps_real_study_concepts(db, no_graph_sync):
    scheduler = ConceptScheduler()
    for word in ("calvin cycle", "mitochondria", "photosynthesis", "atp"):
        assert scheduler.add_concept(word, confidence=0.7, context="ocr") is not None, word


def test_add_concept_stores_explicit_source(db, no_graph_sync):
    # FKT-F-007: ConceptEncounter.source documents 'ocr' | 'browser_extension' |
    # 'manual' (models.py:261); an explicit source must be persisted verbatim.
    from tracker_app.db.models import ConceptEncounter

    scheduler = ConceptScheduler()
    assert scheduler.add_concept(
        "backpropagation",
        confidence=0.7,
        context="browser:New Tab - Wikipedia",
        source="browser_extension",
    ) is not None

    with db() as session:
        rows = session.query(ConceptEncounter).filter(
            ConceptEncounter.concept == "backpropagation"
        ).all()
    assert len(rows) == 1
    assert rows[0].source == "browser_extension"


def test_add_concept_default_source_is_ocr(db, no_graph_sync):
    # FKT-F-007: existing callers (OCR path, api.py, loop.py) call add_concept
    # without a source; the default must keep writing 'ocr'.
    from tracker_app.db.models import ConceptEncounter

    scheduler = ConceptScheduler()
    assert scheduler.add_concept(
        "backpropagation", confidence=0.7, context="ocr"
    ) is not None

    with db() as session:
        rows = session.query(ConceptEncounter).filter(
            ConceptEncounter.concept == "backpropagation"
        ).all()
    assert len(rows) == 1
    assert rows[0].source == "ocr"


def test_get_scheduler_is_singleton():
    # H-2: record_quiz_result must reuse one shared scheduler instead of
    # spawning a throw-away ConceptScheduler on every call.
    from tracker_app.learning.concept_scheduler import get_scheduler
    assert get_scheduler() is get_scheduler()
    assert isinstance(get_scheduler(), ConceptScheduler)


if __name__ == '__main__':
    import sys
    sys.exit(pytest.main([__file__, '-v']))
