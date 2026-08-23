"""Tests: knowledge graph node cap with zero-edge eviction (H-6).

The graph used to grow without bound: every concept gained a 384-dim
embedding node and _load_graph() kept getting slower. _save_graph() now
evicts the lowest-memory_score nodes that have zero edges once the count
exceeds MAX_GRAPH_NODES, so semantic structure (edges) is never destroyed.
"""

import pytest

from tracker_app.tracking import knowledge_graph as kg


@pytest.fixture(autouse=True)
def _clean_graph():
    kg.knowledge_graph.clear()
    yield
    kg.knowledge_graph.clear()


def test_save_graph_evicts_lowest_memory_isolated_nodes(monkeypatch, tmp_path):
    monkeypatch.setattr(kg, "MAX_GRAPH_NODES", 5)
    monkeypatch.setattr(kg, "KNOWLEDGE_GRAPH_PATH", str(tmp_path / "graph.pkl"))

    for name, score in [("a", 0.1), ("b", 0.2), ("c", 0.3)]:
        kg.knowledge_graph.add_node(name, memory_score=score)
    for name, score in [("d", 0.9), ("e", 0.8)]:
        kg.knowledge_graph.add_node(name, memory_score=score)
    kg.knowledge_graph.add_node("g", memory_score=0.95)
    kg.knowledge_graph.add_node("h", memory_score=0.95)
    kg.knowledge_graph.add_edge("g", "h", weight=0.8)  # connected: never evicted

    assert kg.knowledge_graph.number_of_nodes() == 7
    kg._save_graph()

    assert kg.knowledge_graph.number_of_nodes() == 5
    assert "a" not in kg.knowledge_graph  # two lowest zero-edge nodes evicted
    assert "b" not in kg.knowledge_graph
    assert "c" in kg.knowledge_graph
    assert "d" in kg.knowledge_graph
    assert "e" in kg.knowledge_graph
    assert "g" in kg.knowledge_graph and "h" in kg.knowledge_graph


def test_save_graph_never_evicts_connected_nodes(monkeypatch, tmp_path):
    monkeypatch.setattr(kg, "MAX_GRAPH_NODES", 2)
    monkeypatch.setattr(kg, "KNOWLEDGE_GRAPH_PATH", str(tmp_path / "graph.pkl"))

    kg.knowledge_graph.add_node("a", memory_score=0.05)
    kg.knowledge_graph.add_node("b", memory_score=0.05)
    kg.knowledge_graph.add_edge("a", "b", weight=0.9)
    kg.knowledge_graph.add_node("iso", memory_score=0.5)

    kg._save_graph()

    assert kg.knowledge_graph.number_of_nodes() == 2
    assert "iso" not in kg.knowledge_graph
    assert "a" in kg.knowledge_graph and "b" in kg.knowledge_graph


def test_save_graph_within_cap_evicts_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(kg, "MAX_GRAPH_NODES", 3)
    monkeypatch.setattr(kg, "KNOWLEDGE_GRAPH_PATH", str(tmp_path / "graph.pkl"))

    kg.knowledge_graph.add_node("a", memory_score=0.1)
    kg.knowledge_graph.add_node("b", memory_score=0.2)
    kg.knowledge_graph.add_node("c", memory_score=0.3)

    kg._save_graph()

    assert kg.knowledge_graph.number_of_nodes() == 3
    assert set(kg.knowledge_graph.nodes()) == {"a", "b", "c"}
