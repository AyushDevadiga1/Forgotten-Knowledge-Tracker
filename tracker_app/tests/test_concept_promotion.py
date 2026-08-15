"""Tests: tracked-concept -> learning deck promotion (KB backfill).

The Knowledge Base / Review pages read `learning_items` while passive tracking
writes `tracked_concepts`. concept_promotion is the bridge: only KB-worthy
concepts (plausible AND not UI chrome) with enough repeated exposure become
deck items, idempotently.

Run: python -m pytest tracker_app/tests/test_concept_promotion.py -v
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tracker_app.db import models
from tracker_app.db.models import Base, TrackedConcept, LearningItem
from tracker_app.learning import concept_promotion as cp


@pytest.fixture
def db(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(cp, "SessionLocal", TestingSessionLocal)
    return TestingSessionLocal


def _seed(db, concept, freq=5, relevance=0.6):
    with db() as s:
        s.add(TrackedConcept(concept=concept, frequency_count=freq,
                             relevance_score=relevance))
        s.commit()


def _questions(db):
    with db() as s:
        return [i.question for i in s.query(LearningItem).all()]


def test_is_kb_worthy_accepts_real_concepts():
    assert cp.is_kb_worthy("hash table")
    assert cp.is_kb_worthy("pytorch")
    assert cp.is_kb_worthy("big-o notation")              # curated exception
    assert cp.is_kb_worthy("ebbinghaus forgetting curve")  # curated exception


def test_is_kb_worthy_rejects_chrome_and_noise():
    assert not cp.is_kb_worthy("uktantigtaaty")
    assert not cp.is_kb_worthy("srketonviewgoorunferminalhelp")
    assert not cp.is_kb_worthy("explorer")
    assert not cp.is_kb_worthy("context")
    assert not cp.is_kb_worthy("terminal")


def test_backfill_promotes_only_worthy(db):
    _seed(db, "hash table")
    _seed(db, "explorer")
    _seed(db, "uktantigtaaty")
    result = cp.backfill_items(min_frequency=3)
    assert result['promoted'] == ["hash table"]
    assert _questions(db) == ["hash table"]


def test_backfill_is_idempotent(db):
    _seed(db, "hash table")
    first = cp.backfill_items(min_frequency=3)
    second = cp.backfill_items(min_frequency=3)
    assert first['promoted'] == ["hash table"]
    assert second['promoted'] == []
    assert len(_questions(db)) == 1


def test_backfill_skips_fragment_subsumed_by_eligible_phrase(db):
    _seed(db, "cellular respiration", freq=20)
    _seed(db, "cellular", freq=5)
    result = cp.backfill_items(min_frequency=3)
    assert result['promoted'] == ["cellular respiration"]
    assert _questions(db) == ["cellular respiration"]


def test_single_word_kept_when_phrase_below_threshold(db):
    _seed(db, "atp", freq=3)
    _seed(db, "atp energy", freq=2)
    result = cp.backfill_items(min_frequency=3)
    assert "atp" in result['promoted']


def test_backfill_respects_frequency_floor(db):
    _seed(db, "hash table", freq=2)
    result = cp.backfill_items(min_frequency=3)
    assert result['promoted'] == []
    assert _questions(db) == []


def test_promote_concept_uses_context_snippet_as_answer(db):
    from tracker_app.db.models import ConceptEncounter
    _seed(db, "cellular respiration", freq=20)
    with db() as s:
        s.add(ConceptEncounter(concept="cellular respiration", context_snippet="browser:Biology notes"))
        s.commit()
    cp.promote_concept_to_deck("cellular respiration")
    with db() as s:
        item = s.query(LearningItem).filter(LearningItem.question == "cellular respiration").first()
    assert "Biology notes" in item.answer


def test_load_subsuming_phrases_prefilters_eligibility(db):
    _seed(db, "cellular respiration", freq=20)
    _seed(db, "atp energy", freq=2)   # below threshold -> excluded
    _seed(db, "explorer", freq=10)    # UI chrome -> excluded
    phrases = cp._load_subsuming_phrases()
    assert phrases == frozenset({"cellular respiration"})


def test_in_memory_subsumption_avoids_db(monkeypatch):
    def boom():
        raise AssertionError("SessionLocal must not be used with subsuming_phrases")

    monkeypatch.setattr(cp, "SessionLocal", boom)
    phrases = frozenset(["cellular respiration", "atp synthase"])

    assert cp._is_subsumed_single_word("cellular", subsuming_phrases=phrases) is True
    assert cp._is_subsumed_single_word("atp", subsuming_phrases=phrases) is True
    assert cp._is_subsumed_single_word("hash", subsuming_phrases=phrases) is False
    assert cp._is_subsumed_single_word(
        "cellular respiration", subsuming_phrases=phrases
    ) is False
