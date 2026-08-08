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


if __name__ == '__main__':
    import sys
    sys.exit(pytest.main([__file__, '-v']))
