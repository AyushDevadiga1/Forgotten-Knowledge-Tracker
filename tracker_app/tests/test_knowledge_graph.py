"""Tests for knowledge-graph persistence (pkl cache)."""

import pytest

from tracker_app.tracking import knowledge_graph as kg


@pytest.fixture
def isolated_graph_path(tmp_path, monkeypatch):
    """Point KNOWLEDGE_GRAPH_PATH at a temp file for the duration of a test."""
    pkl_path = tmp_path / "graph.pkl"
    monkeypatch.setattr(kg, "KNOWLEDGE_GRAPH_PATH", str(pkl_path))
    return pkl_path


@pytest.fixture
def clean_graph():
    """Snapshot the shared in-memory graph and restore it after the test."""
    original = kg.knowledge_graph.copy()
    yield
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_nodes_from(original.nodes(data=True))
        kg.knowledge_graph.add_edges_from(original.edges(data=True))


def test_save_and_reload_graph(isolated_graph_path, clean_graph):
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("neural network", count=1, memory_score=0.3)
        kg.knowledge_graph.add_node("backpropagation", count=2, memory_score=0.5)
        kg.knowledge_graph.add_edge("neural network", "backpropagation", weight=0.95)

    kg._save_graph()
    assert isolated_graph_path.exists()

    # Simulate a fresh process: empty in-memory graph, then reload from pkl.
    with kg._graph_lock:
        kg.knowledge_graph.clear()
    assert kg._load_graph() is True

    g = kg.knowledge_graph
    assert g.number_of_nodes() == 2
    assert g.nodes["neural network"]["count"] == 1
    assert g.nodes["backpropagation"]["memory_score"] == 0.5
    assert g["neural network"]["backpropagation"]["weight"] == 0.95


def test_load_missing_graph_returns_false(isolated_graph_path, clean_graph):
    assert kg._load_graph() is False


def test_load_corrupt_graph_returns_false(isolated_graph_path, clean_graph):
    isolated_graph_path.write_bytes(b"not a pickle")
    assert kg._load_graph() is False


def test_sync_db_to_graph_is_incremental(isolated_graph_path, clean_graph, monkeypatch):
    """Concepts already in the graph are not re-added on sync."""
    added = []

    def fake_add(concepts):
        added.extend(concepts)

    monkeypatch.setattr(kg, "fetch_concepts_from_db", lambda: ["neural network", "new concept"])
    monkeypatch.setattr(kg, "add_concepts", fake_add)
    monkeypatch.setattr(kg, "_save_graph", lambda: None)

    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("neural network")

    kg.sync_db_to_graph()
    assert added == ["new concept"]
