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
    monkeypatch.setattr(kg, "sync_concept_to_graph", lambda c: None)
    monkeypatch.setattr(kg, "_refresh_all_memory_scores", lambda concepts: None)
    monkeypatch.setattr(kg, "_save_graph", lambda: None)

    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("neural network")

    kg.sync_db_to_graph()
    assert added == ["new concept"]


def test_graph_stats_includes_real_edges(clean_graph):
    """M-7: /graph/stats must return the actual weighted edges among the top
    concepts (the frontend drew fabricated spokes before). Edges to concepts
    outside the visible top set are excluded."""
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("alpha", memory_score=0.9)
        kg.knowledge_graph.add_node("beta", memory_score=0.8)
        kg.knowledge_graph.add_node("gamma", memory_score=0.7)
        # 7 filler nodes at 0.1 + one at 0.0 -> 11 nodes total, so the 0.0
        # node falls outside the top-10 set.
        for i in range(7):
            kg.knowledge_graph.add_node(f"filler{i}", memory_score=0.1)
        kg.knowledge_graph.add_node("low", memory_score=0.0)
        kg.knowledge_graph.add_edge("alpha", "beta", weight=0.98)
        kg.knowledge_graph.add_edge("alpha", "gamma", weight=0.71)
        # edge into a node that is NOT in the top set
        kg.knowledge_graph.add_edge("gamma", "low", weight=0.95)

    stats = kg.get_graph_stats()
    assert stats["top_concepts"][:3] == ["alpha", "beta", "gamma"]
    assert "low" not in stats["top_concepts"]
    assert sorted(stats["edges"]) == sorted([
        ["alpha", "beta", 0.98],
        ["alpha", "gamma", 0.71],
    ])
    # the strongest edge is listed first
    assert stats["edges"][0] == ["alpha", "beta", 0.98]


def test_graph_stats_includes_node_memory_scores(clean_graph):
    """The visible top set must ship per-node live memory scores so the
    frontend force-layout can size/colour nodes honestly (Phase D)."""
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("alpha", memory_score=0.9)
        kg.knowledge_graph.add_node("beta", memory_score=0.8)
        kg.knowledge_graph.add_node("gamma", memory_score=0.7)
        for i in range(7):
            kg.knowledge_graph.add_node(f"filler{i}", memory_score=0.1)
        kg.knowledge_graph.add_node("low", memory_score=0.0)

    stats = kg.get_graph_stats()
    by_name = {n["concept"]: n["memory_score"] for n in stats["nodes"]}
    assert by_name["alpha"] == 0.9
    assert by_name["beta"] == 0.8
    assert by_name["gamma"] == 0.7
    assert "low" not in by_name  # outside the visible top-10 set
    assert len(stats["nodes"]) == len(stats["top_concepts"])
