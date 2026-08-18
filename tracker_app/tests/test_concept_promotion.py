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



def test_promote_reuses_single_db_session(db, monkeypatch):
    """L-5: promotion must not open a second session for the encounter lookup.

    _answer_for used to open its own SessionLocal, so a single promotion
    touched the DB three times. It now reuses the caller's session.
    """
    from tracker_app.db.models import ConceptEncounter

    class _CountingMaker:
        def __init__(self, underlying):
            self._underlying = underlying
            self.count = 0

        def __call__(self):
            self.count += 1
            return self._underlying()

    promote_maker = _CountingMaker(db)
    item_maker = _CountingMaker(db)
    monkeypatch.setattr(cp, "SessionLocal", promote_maker)
    monkeypatch.setattr(
        "tracker_app.learning.learning_tracker.models.SessionLocal", item_maker
    )

    with db() as s:
        s.add(TrackedConcept(concept="atp", frequency_count=5, relevance_score=0.6))
        s.add(ConceptEncounter(concept="atp", context_snippet="browser:ATP notes"))
        s.commit()

    item_id = cp.promote_concept_to_deck("atp", subsuming_phrases=frozenset())
    assert item_id
    assert promote_maker.count == 1   # one session for idempotency + encounter lookup
    assert item_maker.count == 1      # add_learning_item's own session

    with db() as s:
        item = s.query(LearningItem).filter(LearningItem.question == "atp").first()
    assert "ATP notes" in item.answer



def test_curated_exceptions_loads_from_file(monkeypatch, tmp_path):
    """L-6: DATA_DIR/curated_exceptions.txt replaces the built-in set."""
    f = tmp_path / "curated_exceptions.txt"
    f.write_text("# my exceptions\nzipf's law\n\nEbbinghaus Forgetting Curve\n",
                 encoding="utf-8")
    monkeypatch.setattr(cp, "_CURATED_EXCEPTIONS_FILE", f)
    loaded = cp._load_curated_exceptions()

    assert "zipf's law" in loaded
    assert "ebbinghaus forgetting curve" in loaded
    assert "big-o notation" not in loaded          # file replaces the defaults

    monkeypatch.setattr(cp, "CURATED_EXCEPTIONS", loaded)
    assert cp.is_kb_worthy("Zipf's Law")           # case-insensitive match
    assert not cp.is_kb_worthy("xyz123 abc")       # structural gate applies again


def test_curated_exceptions_fallback_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(cp, "_CURATED_EXCEPTIONS_FILE", tmp_path / "missing.txt")
    assert cp._load_curated_exceptions() == cp.CURATED_EXCEPTIONS_DEFAULT


def test_curated_exceptions_fallback_when_file_has_no_entries(monkeypatch, tmp_path):
    f = tmp_path / "curated_exceptions.txt"
    f.write_text("\n  \n# only a comment\n", encoding="utf-8")
    monkeypatch.setattr(cp, "_CURATED_EXCEPTIONS_FILE", f)
    assert cp._load_curated_exceptions() == cp.CURATED_EXCEPTIONS_DEFAULT


def test_curated_exceptions_fallback_on_read_error(monkeypatch, tmp_path):
    class _Boom:
        def exists(self):
            return True

    monkeypatch.setattr(cp, "_CURATED_EXCEPTIONS_FILE", _Boom())
    import builtins

    def boom(*args, **kwargs):
        raise OSError("cannot read")

    monkeypatch.setattr(builtins, "open", boom)
    assert cp._load_curated_exceptions() == cp.CURATED_EXCEPTIONS_DEFAULT
