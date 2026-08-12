"""Tests: knowledge-graph memory_score sync (Phase 11.2).

The graph's memory_score must track the live SM-2/AWFC state — not stay frozen
at the 0.3 assigned at node creation — so the dashboard's average memory and
the micro-quiz's "weakest concept" selection reflect real progress.

Run: python -m pytest tracker_app/tests/test_graph_memory_sync.py -v
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tracker_app.tracking import knowledge_graph as kg
from tracker_app.db import models
from tracker_app.db.models import Base, TrackedConcept


@pytest.fixture
def isolated_graph_path(tmp_path, monkeypatch):
    pkl_path = tmp_path / "graph.pkl"
    monkeypatch.setattr(kg, "KNOWLEDGE_GRAPH_PATH", str(pkl_path))
    return pkl_path


@pytest.fixture
def clean_graph():
    original = kg.knowledge_graph.copy()
    yield
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_nodes_from(original.nodes(data=True))
        kg.knowledge_graph.add_edges_from(original.edges(data=True))
        kg._loaded = False
        kg._last_db_sync = 0.0


@pytest.fixture
def db(monkeypatch):
    """Point SessionLocal (as imported by knowledge_graph + scheduler) at an
    in-memory DB for the duration of the test."""
    engine = create_engine('sqlite:///:memory:')
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "SessionLocal", TestingSessionLocal)
    return TestingSessionLocal


def _add_concept(db, concept, last_seen=None, lambda_p=0.1, attention=50.0,
                 interval=1, strength=2.5):
    with db() as session:
        row = TrackedConcept(
            concept=concept,
            first_seen=last_seen or datetime.utcnow(),
            last_seen=last_seen or datetime.utcnow(),
            next_review=datetime.utcnow(),
            relevance_score=0.8,
            attention_at_encoding=attention,
            lambda_personalised=lambda_p,
            interval=interval,
            memory_strength=strength,
        )
        session.add(row)
        session.commit()
        return row


def _memory_score(concept):
    return kg.knowledge_graph.nodes[concept]['memory_score']


def test_fresh_concept_syncs_to_high_score(isolated_graph_path, clean_graph, db):
    _add_concept(db, "transformer", last_seen=datetime.utcnow())
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("transformer", count=1, memory_score=0.3)

    kg.sync_concept_to_graph("transformer")
    assert _memory_score("transformer") > 0.9   # just reinforced → ~1.0
    assert "interval" in kg.knowledge_graph.nodes["transformer"]


def test_stale_concept_syncs_to_low_score(isolated_graph_path, clean_graph, db):
    old = datetime.utcnow() - timedelta(days=5)
    _add_concept(db, "decay-example", last_seen=old)
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("decay-example", count=1, memory_score=0.3)

    kg.sync_concept_to_graph("decay-example")
    assert _memory_score("decay-example") < 0.3  # decayed — no longer 0.3


def test_add_concepts_uses_live_score_at_creation(isolated_graph_path, clean_graph, db, monkeypatch):
    """New nodes are created with the live DB score, not a hardcoded 0.3."""
    monkeypatch.setattr(kg, "_get_embed_model", lambda: None)
    monkeypatch.setattr(kg, "_get_spacy_vectors", lambda concepts: None)
    old = datetime.utcnow() - timedelta(days=5)
    _add_concept(db, "forgotten-concept", last_seen=old)
    with kg._graph_lock:
        kg.knowledge_graph.clear()

    kg.add_concepts(["forgotten-concept"])
    assert kg.knowledge_graph.nodes["forgotten-concept"]["memory_score"] < 0.3


def test_sync_adds_missing_concept_from_db(isolated_graph_path, clean_graph, db, monkeypatch):
    """A concept the DB gained after the graph was last built must be added on
    first contact — the micro-quiz 'weakest concept' selection and graph stats
    must not serve a graph frozen at first load (mid-session captures)."""
    monkeypatch.setattr(kg, "_get_embed_model", lambda: None)
    monkeypatch.setattr(kg, "_get_spacy_vectors", lambda concepts: None)
    _add_concept(db, "chloroplast", last_seen=datetime.utcnow())
    with kg._graph_lock:
        kg.knowledge_graph.clear()

    kg.sync_concept_to_graph("chloroplast")

    assert "chloroplast" in kg.knowledge_graph
    assert _memory_score("chloroplast") > 0.9   # live AWFC score, not the 0.3 default


def test_sync_skips_concept_absent_from_db(isolated_graph_path, clean_graph, monkeypatch):
    """sync_concept_to_graph for a concept in neither DB nor graph is a no-op —
    it must not resurrect a deleted concept with a fabricated 0.3 score."""
    monkeypatch.setattr(kg, "_get_embed_model", lambda: None)
    monkeypatch.setattr(kg, "_get_spacy_vectors", lambda concepts: None)
    with kg._graph_lock:
        kg.knowledge_graph.clear()

    kg.sync_concept_to_graph("ghost-concept")

    assert "ghost-concept" not in kg.knowledge_graph


def test_schedule_next_review_bounces_memory_score(isolated_graph_path, clean_graph, db):
    """A review resets the retention clock: memory_score goes low -> high."""
    from tracker_app.learning.concept_scheduler import ConceptScheduler
    old = datetime.utcnow() - timedelta(days=5)
    _add_concept(db, "review-me", last_seen=old)
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("review-me", count=1, memory_score=0.3)

    kg.sync_concept_to_graph("review-me")
    low = _memory_score("review-me")
    assert low < 0.3

    ConceptScheduler().schedule_next_review("review-me", quality=5)

    kg.sync_concept_to_graph("review-me")
    high = _memory_score("review-me")
    assert high > 0.9
    assert high > low


if __name__ == '__main__':
    import sys
    sys.exit(pytest.main([__file__, '-v']))
