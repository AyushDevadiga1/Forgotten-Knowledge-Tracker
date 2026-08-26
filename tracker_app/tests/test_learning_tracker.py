"""
Unit Tests: LearningTracker
============================
Tests core CRUD and review logic with isolated SQLAlchemy in-memory DB.
Run: python -m pytest tracker_app/tests/test_learning_tracker.py -v
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tracker_app.learning.learning_tracker import LearningTracker
from tracker_app.learning import concept_scheduler as cs
from tracker_app.db import models
from tracker_app.db.models import Base, LearningItem, ReviewHistory, TrackedConcept


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "SessionLocal", TestingSessionLocal)
    return TestingSessionLocal


@pytest.fixture
def tracker(db):
    return LearningTracker()


# --- Add / Get ---


def test_add_valid_item_returns_id(tracker):
    item_id = tracker.add_learning_item("Q?", "A.")
    assert isinstance(item_id, str)
    assert len(item_id) > 0


def test_add_item_persisted_in_db(tracker, db):
    tracker.add_learning_item("What is recursion?", "A function calls itself")
    with db() as s:
        item = s.query(LearningItem).first()
        assert item is not None
        assert item.question == "What is recursion?"


def test_get_items_due_empty_db(tracker):
    assert tracker.get_items_due() == []


def test_new_item_is_immediately_due(tracker):
    tracker.add_learning_item("Q?", "A.")
    due = tracker.get_items_due()
    assert len(due) == 1


def test_stats_with_empty_db(tracker):
    stats = tracker.get_learning_stats()
    assert stats["total_items"] == 0


def test_stats_reflect_added_items(tracker):
    tracker.add_learning_item("Q1", "A1")
    tracker.add_learning_item("Q2", "A2")
    stats = tracker.get_learning_stats()
    assert stats["total_items"] == 2


# --- Review ---


def test_review_updates_repetitions(tracker):
    item_id = tracker.add_learning_item("Q?", "A.")
    tracker.record_review(item_id, quality_rating=5)
    with models.SessionLocal() as db:
        item = db.query(LearningItem).filter(LearningItem.id == item_id).first()
        assert item.repetitions > 0


def test_review_history_recorded(tracker):
    item_id = tracker.add_learning_item("Q?", "A.")
    tracker.record_review(item_id, quality_rating=3)
    with models.SessionLocal() as db:
        count = db.query(ReviewHistory).filter(ReviewHistory.item_id == item_id).count()
        assert count == 1


def test_review_sm2_persists_last_review_date(tracker):
    item_id = tracker.add_learning_item("Q?", "A.")
    tracker.record_review(item_id, quality_rating=5, algorithm="sm2")
    item = tracker.get_item(item_id)
    assert item["last_review_date"] is not None
    with models.SessionLocal() as db:
        row = db.query(LearningItem).filter(LearningItem.id == item_id).first()
        assert row.last_review_date is not None


# --- H1: Deck-to-concept feedback loop ---


def _setup_concept_feedback(db, monkeypatch):
    """Helper: seed a tracked concept and patch ConceptScheduler."""
    from tracker_app.learning.concept_scheduler import ConceptScheduler

    scheduler = ConceptScheduler()
    monkeypatch.setattr(cs, "SessionLocal", db)
    monkeypatch.setattr(cs, "get_scheduler", lambda: scheduler)
    return scheduler


def test_review_syncs_concept_sm2(tracker, db, monkeypatch):
    _setup_concept_feedback(db, monkeypatch)

    with db() as s:
        s.add(TrackedConcept(concept="hash table", frequency_count=5, relevance_score=0.6))
        s.commit()

    item_id = tracker.add_learning_item("hash table", "A data structure")
    tracker.record_review(item_id, quality_rating=5)

    with db() as s:
        tc = s.query(TrackedConcept).filter(TrackedConcept.concept == "hash table").first()
        assert tc.repetitions > 0
        assert tc.next_review is not None


def test_review_noop_when_no_matching_concept(tracker, db, monkeypatch):
    _setup_concept_feedback(db, monkeypatch)

    item_id = tracker.add_learning_item("unique question", "answer")
    tracker.record_review(item_id, quality_rating=4)

    with db() as s:
        tc = s.query(TrackedConcept).filter(TrackedConcept.concept == "unique question").first()
        assert tc is None


def test_review_idempotent_on_concept(tracker, db, monkeypatch):
    _setup_concept_feedback(db, monkeypatch)

    with db() as s:
        s.add(TrackedConcept(concept="pytorch", frequency_count=3, relevance_score=0.7))
        s.commit()

    item_id = tracker.add_learning_item("pytorch", "Deep learning framework")
    tracker.record_review(item_id, quality_rating=5)
    tracker.record_review(item_id, quality_rating=5)

    with db() as s:
        tc = s.query(TrackedConcept).filter(TrackedConcept.concept == "pytorch").first()
        assert tc is not None
        assert tc.repetitions == 2
