"""Tests: micro-quiz candidate pool is content-backed (P3/D3, capture-fidelity).

The quiz must never burn a question on a concept that has no captured content:
the pool is built from persisted ConceptEncounter excerpts (len > 8, not 'ocr'),
and generate_micro_quiz() returns None when the pool is empty.
"""

import networkx as nx
import pytest

from tracker_app.tracking import quiz_engine


def _graph():
    G = nx.Graph()
    for name in ["alpha", "beta", "gamma", "delta"]:
        G.add_node(name, memory_score=0.2)
    return G


def _pool():
    return {n: f"{n} is explained in the captured study notes" for n in ["alpha", "beta", "gamma", "delta"]}


def test_quiz_returns_none_when_no_concept_has_content(monkeypatch):
    monkeypatch.setattr(quiz_engine, "_content_backed_pool", lambda: {})
    assert quiz_engine.generate_micro_quiz(_graph()) is None


def test_quiz_uses_only_content_backed_concepts(monkeypatch):
    monkeypatch.setattr(quiz_engine, "_content_backed_pool", lambda: {"alpha": "alpha is covered in captured text"})
    quiz = quiz_engine.generate_micro_quiz(_graph())
    assert quiz is not None
    assert quiz["concept"] == "alpha"
    assert quiz["all_options"][quiz["correct_index"]] == "alpha"
    assert quiz["memory_score"] == pytest.approx(0.2)


def test_quiz_stem_references_captured_material(monkeypatch):
    monkeypatch.setattr(quiz_engine, "_content_backed_pool", lambda: _pool())
    quiz = quiz_engine.generate_micro_quiz(_graph())
    assert quiz is not None
    assert "Which of these concepts does this captured material cover?" in quiz["question"]
    assert "alpha is explained in the captured study notes" in quiz["question"]


def test_content_backed_pool_requires_real_persisted_excerpt(monkeypatch):
    from datetime import datetime, timedelta

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from tracker_app.db import models
    from tracker_app.db.models import Base, ConceptEncounter, TrackedConcept

    engine = create_engine("sqlite:///:memory:")
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "SessionLocal", TestSession)

    old = datetime.utcnow() - timedelta(days=30)
    with TestSession() as s:
        s.add(TrackedConcept(concept="real concept", frequency_count=5, relevance_score=0.6))
        s.add(TrackedConcept(concept="placeholder", frequency_count=5, relevance_score=0.6))
        s.add(TrackedConcept(concept="tiny", frequency_count=5, relevance_score=0.6))
        s.add(
            ConceptEncounter(
                concept="real concept",
                timestamp=old,
                context_snippet="real concept has many details to remember",
            )
        )
        s.add(ConceptEncounter(concept="placeholder", timestamp=old, context_snippet="ocr"))
        s.add(ConceptEncounter(concept="tiny", timestamp=old, context_snippet="short"))
        s.commit()

    assert quiz_engine._content_backed_pool() == {"real concept": "real concept has many details to remember"}
