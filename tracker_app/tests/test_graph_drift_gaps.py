"""Tests: concept drift keywords, dead-branch collapse, and gap embeddings.

Covers Phase 11.3 (drift must receive real session concepts instead of []),
Phase 11.4 (dead 'stable' branch collapsed), and Phase 11.5 (gap detection
reuses the node embeddings that built the edges instead of loading spaCy).

Run: python -m pytest tracker_app/tests/test_graph_drift_gaps.py -v
"""

import pytest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tracker_app.tracking import knowledge_graph as kg
from tracker_app.db import models
from tracker_app.db.models import Base, ConceptEncounter


@pytest.fixture
def clean_graph():
    """Snapshot the shared in-memory graph and restore it after the test."""
    original = kg.knowledge_graph.copy()
    yield
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_nodes_from(original.nodes(data=True))
        kg.knowledge_graph.add_edges_from(original.edges(data=True))


@pytest.fixture
def db(monkeypatch):
    """Point SessionLocal (as imported by knowledge_graph) at an in-memory DB."""
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "SessionLocal", TestingSessionLocal)
    return TestingSessionLocal


@pytest.fixture
def no_graph_reload(monkeypatch):
    """Skip the pkl/DB bootstrap inside drift & gap functions."""
    monkeypatch.setattr(kg, "_ensure_graph_loaded", lambda: None)


def _add_encounter(db, concept, ts):
    with db() as session:
        session.add(ConceptEncounter(concept=concept, timestamp=ts))
        session.commit()


def test_get_session_concepts_returns_recent_encounters(db, monkeypatch):
    """No active session -> fall back to the last 15 minutes (UTC)."""
    monkeypatch.setattr("tracker_app.tracking.session_state.get_status", lambda: {"active": False, "started_at": None})
    now = datetime.utcnow()
    _add_encounter(db, "recent concept", now)
    _add_encounter(db, "stale concept", now - timedelta(hours=2))

    result = kg.get_session_concepts()
    assert "recent concept" in result
    assert "stale concept" not in result


def test_get_session_concepts_uses_active_session_start(db, monkeypatch):
    """Active session -> only encounters since session start are returned."""
    started = datetime.utcnow() - timedelta(minutes=30)
    monkeypatch.setattr(
        "tracker_app.tracking.session_state.get_status", lambda: {"active": True, "started_at": started.isoformat()}
    )
    _add_encounter(db, "in-session", datetime.utcnow() - timedelta(minutes=10))
    _add_encounter(db, "before-session", started - timedelta(minutes=5))

    result = kg.get_session_concepts()
    assert "in-session" in result
    assert "before-session" not in result


def test_drift_unknown_concept_reports_new(clean_graph, no_graph_reload):
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("known", embedding=[], count=1)

    result = kg.compute_concept_drift("unknown", ["known"])
    assert result["status"] == "new"
    assert result["drift_score"] == 0.0
    assert result["co_concepts_now"] == ["known"]


def test_drift_uses_real_session_keywords(clean_graph, no_graph_reload):
    """Session keywords change the drift score vs. an empty keyword list."""
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("transformer", embedding=[], count=1)
        kg.knowledge_graph.add_node("attention", embedding=[], count=1)
        kg.knowledge_graph.add_node("latent space", embedding=[], count=1)
        kg.knowledge_graph.add_edge("transformer", "attention", weight=0.9)
        kg.knowledge_graph.add_edge("transformer", "latent space", weight=0.2)

    result = kg.compute_concept_drift("transformer", ["attention", "self-supervised"])
    assert result["status"] == "stable"
    assert "attention" in result["co_concepts_historic"]
    assert "latent space" not in result["co_concepts_historic"]
    assert 0.0 < result["drift_score"] < 1.0


def test_drift_evolving_when_session_context_disjoint(clean_graph, no_graph_reload):
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("transformer", embedding=[], count=1)
        kg.knowledge_graph.add_node("attention", embedding=[], count=1)
        kg.knowledge_graph.add_edge("transformer", "attention", weight=0.9)

    result = kg.compute_concept_drift("transformer", ["self-supervised", "fine-tuning"])
    assert result["status"] == "evolving"
    assert result["drift_score"] == 1.0


def test_drift_stagnant_without_current_neighbours(clean_graph, no_graph_reload):
    """No current session co-concepts -> 'stagnant', not the dead 'stable'."""
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("transformer", embedding=[], count=1)
        kg.knowledge_graph.add_node("attention", embedding=[], count=1)
        kg.knowledge_graph.add_edge("transformer", "attention", weight=0.9)

    result = kg.compute_concept_drift("transformer", [])
    assert result["status"] == "stagnant"


def test_find_knowledge_gaps_uses_node_embeddings(clean_graph, no_graph_reload):
    """Gap detection must agree with edge building (same node embeddings)."""
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("attention", embedding=[1.0, 0.0, 0.0], count=1)
        kg.knowledge_graph.add_node("self-attention", embedding=[0.9, 0.1, 0.0], count=1)
        kg.knowledge_graph.add_node("layer norm", embedding=[0.8, 0.2, 0.0], count=1)
        kg.knowledge_graph.add_node("keyboard shortcut", embedding=[0.0, 0.0, 1.0], count=1)
        kg.knowledge_graph.add_edge("attention", "self-attention", weight=0.9)

    gaps = kg.find_knowledge_gaps(top_k=5)
    names = [g["gap_concept"] for g in gaps]
    assert "layer norm" in names
    assert "keyboard shortcut" not in names
    for g in gaps:
        assert 0.0 <= g["score"] <= 1.0


def test_find_knowledge_gaps_empty_without_embeddings(clean_graph, no_graph_reload):
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("a", embedding=[], count=1)
        kg.knowledge_graph.add_node("b", embedding=[], count=1)
        kg.knowledge_graph.add_node("c", embedding=[], count=1)
        kg.knowledge_graph.add_node("d", embedding=[], count=1)
        kg.knowledge_graph.add_edge("a", "b", weight=0.9)

    assert kg.find_knowledge_gaps() == []


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
