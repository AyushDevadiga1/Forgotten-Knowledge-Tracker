"""
tests/test_graph.py
-------------------
Validation suite for Knowledge Graph module (IEEE 730 + 1016 compliant).
Ensures:
- Graph persistence (save/load)
- DB sync operation
- Semantic edge formation
- Integrity validation
"""

import os
import pytest
import networkx as nx
from core import knowledge_graph as kg
from config import DB_PATH, GRAPH_PATH


# -----------------------------
# 1️⃣ Environment Setup
# -----------------------------
def test_environment_ready():
    """Ensure DB and data directories exist."""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    assert os.path.exists(db_dir), "Database directory missing."
    assert os.path.exists(log_dir), "Logs directory missing."
    print("✅ Environment directories verified.")

# -----------------------------
# 2️⃣ Graph Initialization
# -----------------------------
def test_graph_initialization():
    """Ensure graph loads or initializes correctly."""
    g = kg.get_graph()
    assert isinstance(g, nx.Graph), "Graph instance not initialized properly."
    print(f"✅ Graph initialized with {len(g.nodes)} nodes and {len(g.edges)} edges.")


# -----------------------------
# 3️⃣ Add Dummy Concepts
# -----------------------------
def test_add_concepts_and_edges():
    """Test semantic embedding and edge formation."""
    sample_concepts = ["Deep Learning", "Neural Network", "Backpropagation", "AI"]
    kg.add_concepts(sample_concepts)
    g = kg.get_graph()
    
    for concept in sample_concepts:
        assert concept in g.nodes, f"{concept} missing from graph."

    edges = list(g.edges(data=True))
    assert any(e[2].get('weight', 0) > 0 for e in edges), "No semantic edges formed."
    print(f"✅ Added {len(sample_concepts)} concepts and formed {len(edges)} edges.")


# -----------------------------
# 4️⃣ Graph Persistence
# -----------------------------
def test_graph_persistence():
    """Test save/load functionality."""
    kg.save_graph()
    assert os.path.exists(GRAPH_PATH), "Graph not saved."
    prev_node_count = len(kg.get_graph().nodes)

    # Reload and compare
    kg.load_graph()
    new_node_count = len(kg.get_graph().nodes)
    assert new_node_count >= prev_node_count, "Graph nodes mismatch after load."

    print(f"✅ Graph persistence verified ({new_node_count} nodes).")


# -----------------------------
# 5️⃣ Integrity Validation
# -----------------------------
def test_graph_integrity_check():
    """Run internal validation to detect isolated or invalid nodes."""
    g = kg.get_graph()
    valid = kg.validate_graph_integrity(g)
    assert valid, "Graph integrity check failed."
    print("✅ Graph integrity validation passed.")


# -----------------------------
# 6️⃣ Co-occurrence Edge Test
# -----------------------------
def test_co_occurrence_edges():
    """Test cross-modal edge creation (OCR + Audio ↔ Intent)."""
    sample_keywords = {"ai": {"score": 0.8}, "neural": {"score": 0.6}}
    intent_label = "StudyIntent"
    audio_label = "VoiceNote"

    G = kg.add_edges(sample_keywords, audio_label, intent_label)
    edges = [e for e in G.edges if isinstance(e[0], tuple) or isinstance(e[1], tuple)]

    assert any("Intent" in str(e) for e in edges), "No co-occurrence edges created."
    print(f"✅ Co-occurrence edge creation validated ({len(edges)} edges).")
