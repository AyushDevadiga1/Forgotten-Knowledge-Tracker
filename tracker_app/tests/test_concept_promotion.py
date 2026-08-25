"""Tests: tracked-concept -> triage queue -> learning deck promotion.

Concepts now route through a triage queue before being promoted to the deck.
backfill_items() and promote_concept_to_deck() add to the queue.
approve_triage() promotes from queue to deck.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tracker_app.db import models
from tracker_app.db.models import Base, TrackedConcept, LearningItem, TriageQueue
from tracker_app.learning import concept_promotion as cp


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(cp, "SessionLocal", TestingSessionLocal)
    return TestingSessionLocal


def _seed(db, concept, freq=5, relevance=0.6):
    with db() as s:
        s.add(TrackedConcept(concept=concept, frequency_count=freq, relevance_score=relevance))
        s.commit()


def _questions(db):
    with db() as s:
        return [i.question for i in s.query(LearningItem).all()]


def _triage_concepts(db, status="pending"):
    with db() as s:
        return [t.concept for t in s.query(TriageQueue).filter(TriageQueue.status == status).all()]


def test_is_kb_worthy_accepts_real_concepts():
    assert cp.is_kb_worthy("hash table")
    assert cp.is_kb_worthy("pytorch")
    assert cp.is_kb_worthy("big-o notation")
    assert cp.is_kb_worthy("ebbinghaus forgetting curve")


def test_is_kb_worthy_rejects_chrome_and_noise():
    assert not cp.is_kb_worthy("uktantigtaaty")
    assert not cp.is_kb_worthy("srketonviewgoorunferminalhelp")
    assert not cp.is_kb_worthy("explorer")
    assert not cp.is_kb_worthy("context")
    assert not cp.is_kb_worthy("terminal")


def test_backfill_queues_only_worthy(db):
    _seed(db, "hash table")
    _seed(db, "explorer")
    _seed(db, "uktantigtaaty")
    result = cp.backfill_items(min_frequency=3)
    assert result["promoted"] == ["hash table"]
    assert _triage_concepts(db) == ["hash table"]
    assert _questions(db) == []


def test_backfill_is_idempotent(db):
    _seed(db, "hash table")
    first = cp.backfill_items(min_frequency=3)
    second = cp.backfill_items(min_frequency=3)
    assert first["promoted"] == ["hash table"]
    assert second["promoted"] == []
    assert len(_triage_concepts(db)) == 1


def test_backfill_skips_fragment_subsumed_by_eligible_phrase(db):
    _seed(db, "cellular respiration", freq=20)
    _seed(db, "cellular", freq=5)
    result = cp.backfill_items(min_frequency=3)
    assert result["promoted"] == ["cellular respiration"]
    assert _triage_concepts(db) == ["cellular respiration"]


def test_single_word_kept_when_phrase_below_threshold(db):
    _seed(db, "atp", freq=3)
    _seed(db, "atp energy", freq=2)
    result = cp.backfill_items(min_frequency=3)
    assert "atp" in result["promoted"]


def test_backfill_respects_frequency_floor(db):
    _seed(db, "hash table", freq=2)
    result = cp.backfill_items(min_frequency=3)
    assert result["promoted"] == []
    assert _triage_concepts(db) == []


def test_promote_adds_to_triage_queue(db):
    _seed(db, "cellular respiration", freq=20)
    entry_id = cp.promote_concept_to_deck("cellular respiration")
    assert entry_id is not None
    assert "cellular respiration" in _triage_concepts(db)
    assert _questions(db) == []


def test_approve_triage_promotes_to_deck(db):
    _seed(db, "cellular respiration", freq=20)
    entry_id = cp.promote_concept_to_deck("cellular respiration")
    item_id = cp.approve_triage(entry_id)
    assert item_id is not None
    assert "cellular respiration" in _questions(db)
    assert _triage_concepts(db) == []
    assert _triage_concepts(db, status="approved") == ["cellular respiration"]


def test_reject_triage_removes_from_queue(db):
    _seed(db, "cellular respiration", freq=20)
    entry_id = cp.promote_concept_to_deck("cellular respiration")
    result = cp.reject_triage(entry_id)
    assert result is True
    assert _triage_concepts(db) == []
    assert _triage_concepts(db, status="rejected") == ["cellular respiration"]
    assert _questions(db) == []


def test_promote_is_idempotent(db):
    _seed(db, "cellular respiration", freq=20)
    first = cp.promote_concept_to_deck("cellular respiration")
    second = cp.promote_concept_to_deck("cellular respiration")
    assert second is None
    assert len(_triage_concepts(db)) == 1


def test_promote_reuses_single_db_session(db, monkeypatch):
    from tracker_app.db.models import ConceptEncounter

    _seed(db, "atp", freq=5)
    with db() as s:
        s.add(ConceptEncounter(concept="atp", context_snippet="browser:ATP notes"))
        s.commit()

    entry_id = cp.promote_concept_to_deck("atp", subsuming_phrases=frozenset())
    assert entry_id is not None

    entry = db().query(TriageQueue).filter(TriageQueue.id == entry_id).first()
    assert "ATP notes" in entry.answer


def test_get_triage_entries(db):
    _seed(db, "hash table", freq=5)
    _seed(db, "pytorch", freq=5)
    cp.promote_concept_to_deck("hash table")
    cp.promote_concept_to_deck("pytorch")

    entries = cp.get_triage_entries(status="pending")
    assert len(entries) == 2
    concepts = {e["concept"] for e in entries}
    assert concepts == {"hash table", "pytorch"}


def test_curated_exceptions_loads_from_file(monkeypatch, tmp_path):
    f = tmp_path / "curated_exceptions.txt"
    f.write_text("# my exceptions\nzipf's law\n\nEbbinghaus Forgetting Curve\n", encoding="utf-8")
    monkeypatch.setattr(cp, "_CURATED_EXCEPTIONS_FILE", f)
    loaded = cp._load_curated_exceptions()

    assert "zipf's law" in loaded
    assert "ebbinghaus forgetting curve" in loaded
    assert "big-o notation" not in loaded

    monkeypatch.setattr(cp, "CURATED_EXCEPTIONS", loaded)
    assert cp.is_kb_worthy("Zipf's Law")
    assert not cp.is_kb_worthy("xyz123 abc")


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
