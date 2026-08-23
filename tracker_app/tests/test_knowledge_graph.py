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
        kg._loaded = False
        kg._last_db_sync = 0.0


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
        assert kg._load_graph_locked() is True

    g = kg.knowledge_graph
    assert g.number_of_nodes() == 2
    assert g.nodes["neural network"]["count"] == 1
    assert g.nodes["backpropagation"]["memory_score"] == 0.5
    assert g["neural network"]["backpropagation"]["weight"] == 0.95


def test_load_missing_graph_returns_false(isolated_graph_path, clean_graph):
    with kg._graph_lock:
        assert kg._load_graph_locked() is False


def test_load_corrupt_graph_returns_false(isolated_graph_path, clean_graph):
    isolated_graph_path.write_bytes(b"not a pickle")
    with kg._graph_lock:
        assert kg._load_graph_locked() is False


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


def test_ensure_graph_loaded_reconciles_mid_process(clean_graph, monkeypatch):
    """Concepts captured after the first load must appear in the graph within
    the resync window — quiz selection / stats must not serve a graph frozen at
    first load for the whole process lifetime."""
    clock = [0.0]
    monkeypatch.setattr(kg.time, "monotonic", lambda: clock[0])

    db_concepts = ["alpha", "beta"]  # alpha from pkl, beta new in DB

    def fake_fetch():
        return list(db_concepts)

    def fake_add(concepts):
        for c in concepts:
            with kg._graph_lock:
                kg.knowledge_graph.add_node(c, count=1, memory_score=0.5)

    monkeypatch.setattr(kg, "_load_graph_locked", lambda: True)
    monkeypatch.setattr(kg, "fetch_concepts_from_db", fake_fetch)
    monkeypatch.setattr(kg, "add_concepts", fake_add)
    monkeypatch.setattr(kg, "_refresh_all_memory_scores", lambda concepts: None)
    monkeypatch.setattr(kg, "_save_graph", lambda: None)

    with kg._graph_lock:
        kg.knowledge_graph.clear()  # fresh process: pkl+DB bootstrap runs

    kg.get_graph()
    assert "alpha" in kg.knowledge_graph  # from the simulated pkl load
    assert "beta" in kg.knowledge_graph  # reconciled on first load

    # A concept the DB gains mid-process is not visible yet...
    db_concepts.append("gamma")
    kg.get_graph()
    assert "gamma" not in kg.knowledge_graph

    # ...but appears after the resync window elapses, without a restart.
    clock[0] = kg.DB_SYNC_INTERVAL_SECONDS + 1
    kg.get_graph()
    assert "gamma" in kg.knowledge_graph


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
    assert sorted(stats["edges"]) == sorted(
        [
            ["alpha", "beta", 0.98],
            ["alpha", "gamma", 0.71],
        ]
    )
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


class _CountingLock:
    def __init__(self):
        self.acquires = 0

    def acquire(self, *args, **kwargs):
        self.acquires += 1

    def release(self, *args, **kwargs):
        pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()


def test_load_graph_renamed_to_locked_contract(clean_graph):
    # M-9: the loader is explicitly a lock-holding helper, never a self-locking
    # entry point.
    assert not hasattr(kg, "_load_graph")
    assert hasattr(kg, "_load_graph_locked")


def test_load_graph_locked_does_not_acquire_lock(isolated_graph_path, clean_graph, monkeypatch):
    with kg._graph_lock:
        kg.knowledge_graph.add_node("neural network", count=1, memory_score=0.3)
    kg._save_graph()

    lock = _CountingLock()
    monkeypatch.setattr(kg, "_graph_lock", lock)
    with lock:  # the caller holds the lock
        assert kg._load_graph_locked() is True
    assert lock.acquires == 1  # only the caller's acquire, never a re-acquire


def test_sync_db_to_graph_force_ensures_loaded(clean_graph, monkeypatch):
    # F-6: force=True bootstraps the in-memory graph before reconciling.
    ensured = []
    monkeypatch.setattr(kg, "_ensure_graph_loaded", lambda: ensured.append(1))
    monkeypatch.setattr(kg, "fetch_concepts_from_db", lambda: [])
    monkeypatch.setattr(kg, "add_concepts", lambda concepts: None)
    monkeypatch.setattr(kg, "_refresh_all_memory_scores", lambda concepts: None)
    monkeypatch.setattr(kg, "_save_graph", lambda: None)
    with kg._graph_lock:
        kg.knowledge_graph.clear()
    stats = kg.sync_db_to_graph(force=True)
    assert ensured == [1]
    assert stats == {"nodes": 0, "edges": 0, "synced": 0}


def test_sync_db_to_graph_force_adds_missing_and_reports_stats(clean_graph, monkeypatch):
    # F-6: only DB concepts missing from the graph are reported as "synced".
    added = []
    monkeypatch.setattr(kg, "_ensure_graph_loaded", lambda: None)
    monkeypatch.setattr(kg, "fetch_concepts_from_db", lambda: ["alpha", "new concept"])
    monkeypatch.setattr(kg, "add_concepts", lambda concepts: added.extend(concepts))
    monkeypatch.setattr(kg, "_refresh_all_memory_scores", lambda concepts: None)
    monkeypatch.setattr(kg, "_save_graph", lambda: None)
    with kg._graph_lock:
        kg.knowledge_graph.clear()
        kg.knowledge_graph.add_node("alpha")
    stats = kg.sync_db_to_graph(force=True)
    assert added == ["new concept"]
    assert stats == {"nodes": 1, "edges": 0, "synced": 1}


def test_sync_db_to_graph_returns_zero_stats_on_error(clean_graph, monkeypatch):
    # F-6: a failing reconcile is contained and reports zero stats instead of
    # raising through to the endpoint.
    monkeypatch.setattr(kg, "_ensure_graph_loaded", lambda: None)

    def boom():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(kg, "fetch_concepts_from_db", boom)
    monkeypatch.setattr(kg, "_refresh_all_memory_scores", lambda concepts: None)
    monkeypatch.setattr(kg, "_save_graph", lambda: None)
    stats = kg.sync_db_to_graph(force=True)
    assert stats == {"nodes": 0, "edges": 0, "synced": 0}


def test_sync_db_to_graph_skips_save_when_clean(clean_graph, monkeypatch):
    """sync_db_to_graph() must not pickle when nothing changed (dirty flag)."""
    monkeypatch.setattr(kg, "_ensure_graph_loaded", lambda: None)
    monkeypatch.setattr(kg, "fetch_concepts_from_db", lambda: ["alpha"])
    monkeypatch.setattr(kg, "_refresh_all_memory_scores", lambda concepts: None)

    # Pre-populate graph so "alpha" is not new and scores are unchanged.
    kg.knowledge_graph.add_node("alpha", memory_score=0.5, count=1)

    saves = []
    monkeypatch.setattr(kg, "_save_graph", lambda: saves.append(1))
    kg._graph_dirty = False  # start clean
    kg.sync_db_to_graph(force=True)
    assert saves == [], "_save_graph() called when graph was clean"


def test_sync_db_to_graph_saves_on_new_concept(clean_graph, monkeypatch):
    """sync_db_to_graph() must save after adding a new node."""
    monkeypatch.setattr(kg, "_ensure_graph_loaded", lambda: None)
    monkeypatch.setattr(kg, "fetch_concepts_from_db", lambda: ["brand-new"])
    monkeypatch.setattr(kg, "_refresh_all_memory_scores", lambda concepts: None)

    saves = []
    monkeypatch.setattr(kg, "_save_graph", lambda: saves.append(1))
    kg._graph_dirty = False
    kg.sync_db_to_graph(force=True)
    assert saves == [1], "_save_graph() was not called after new node"


def test_sync_db_to_graph_saves_on_score_change(clean_graph, monkeypatch):
    """sync_db_to_graph() must save when a memory score actually changes."""
    monkeypatch.setattr(kg, "_ensure_graph_loaded", lambda: None)
    monkeypatch.setattr(kg, "fetch_concepts_from_db", lambda: ["beta"])

    kg.knowledge_graph.add_node("beta", memory_score=0.5, count=1)

    def fake_refresh(concepts):
        kg.knowledge_graph.nodes["beta"]["memory_score"] = 0.9
        kg._graph_dirty = True

    monkeypatch.setattr(kg, "_refresh_all_memory_scores", fake_refresh)

    saves = []
    monkeypatch.setattr(kg, "_save_graph", lambda: saves.append(1))
    kg._graph_dirty = False
    kg.sync_db_to_graph(force=True)
    assert saves == [1], "_save_graph() was not called when score changed"


def test_sync_db_to_graph_skips_save_when_score_unchanged(clean_graph, monkeypatch):
    """sync_db_to_graph() must not save when scores are re-read but identical."""
    monkeypatch.setattr(kg, "_ensure_graph_loaded", lambda: None)
    monkeypatch.setattr(kg, "fetch_concepts_from_db", lambda: ["gamma"])

    kg.knowledge_graph.add_node("gamma", memory_score=0.73, count=1)

    def fake_refresh(concepts):
        pass  # scores stay at 0.73

    monkeypatch.setattr(kg, "_refresh_all_memory_scores", fake_refresh)

    saves = []
    monkeypatch.setattr(kg, "_save_graph", lambda: saves.append(1))
    kg._graph_dirty = False
    kg.sync_db_to_graph(force=True)
    assert saves == [], "_save_graph() called when score was unchanged"
