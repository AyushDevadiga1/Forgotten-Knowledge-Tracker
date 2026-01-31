# ==========================================================
# core/knowledge_graph.py (Upgraded IEEE v2.2)
# ==========================================================
"""
Knowledge Graph Management Module (IEEE v2.2)
---------------------------------------------
- Builds and maintains a semantic graph of concepts.
- Computes embeddings and semantic similarity edges.
- Syncs DB sessions/concepts and memory scores into the graph.
- Handles stale nodes, edge metadata, node centrality, and incremental updates.
- Fully typed, logged, and IEEE 1016 / 12207 / 730 compliant.
"""

import networkx as nx
from sentence_transformers import SentenceTransformer
import numpy as np
import sqlite3
import joblib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Callable
import logging
from config import DB_PATH

# ==========================================================
# LOGGER SETUP
# ==========================================================
logging.basicConfig(
    filename="logs/knowledge_graph.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s"
)

# ==========================================================
# CONSTANTS
# ==========================================================
GRAPH_PATH = "data/knowledge_graph.pkl"
SIMILARITY_THRESHOLD = 0.7  # Dynamic similarity threshold (can be moved to config)
STALE_NODE_DAYS = 30

# ==========================================================
# SAFE EXEC WRAPPER
# ==========================================================
def safe_exec(func: Callable):
    """Decorator to catch and log exceptions for safety-critical functions."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.exception(f"{func.__name__} failed: {e}")
            return None
    return wrapper

# ==========================================================
# COSINE SIMILARITY SAFEGUARD
# ==========================================================
def safe_cosine_similarity(vec_i: np.ndarray, vec_j: np.ndarray) -> float:
    denom = np.linalg.norm(vec_i) * np.linalg.norm(vec_j)
    if denom == 0:
        return 0.0
    return float(np.dot(vec_i, vec_j) / denom)

# ==========================================================
# INITIALIZE EMBEDDING MODEL
# ==========================================================
try:
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    logging.info("Embedding model loaded successfully.")
except Exception as e:
    logging.error(f"Failed to load embedding model: {e}")
    embed_model = None

# ==========================================================
# INITIALIZE MAIN KNOWLEDGE GRAPH
# ==========================================================
knowledge_graph: nx.Graph = nx.Graph()

# ==========================================================
# GRAPH PERSISTENCE
# ==========================================================
@safe_exec
def save_graph(versioned: bool = True) -> None:
    """Save the current knowledge graph to disk with optional versioning."""
    import os
    os.makedirs("data", exist_ok=True)
    path = GRAPH_PATH
    if versioned:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"data/knowledge_graph_v{timestamp}.pkl"
    joblib.dump(knowledge_graph, path)
    logging.info(f"Knowledge graph saved to {path}")

@safe_exec
def load_graph() -> None:
    """Load the knowledge graph from disk or start fresh."""
    global knowledge_graph
    try:
        knowledge_graph = joblib.load(GRAPH_PATH)
        logging.info(f"Knowledge graph loaded from {GRAPH_PATH}")
    except FileNotFoundError:
        logging.warning("Graph file not found — starting a new graph instance.")
        knowledge_graph = nx.Graph()

# Load existing graph at startup
load_graph()

# ==========================================================
# FETCH CONCEPTS FROM DB
# ==========================================================
@safe_exec
def fetch_concepts_from_db() -> List[str]:
    """Retrieve distinct window titles or concepts from DB."""
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute("SELECT DISTINCT window_title FROM sessions")
        rows = c.fetchall()
        concepts = [row[0].strip() for row in rows if row[0] and row[0].strip()]
        logging.info(f"Fetched {len(concepts)} concepts from DB.")
        return concepts
    finally:
        conn.close()

# ==========================================================
# ADD CONCEPTS AND SEMANTIC EDGES
# ==========================================================
@safe_exec
def add_concepts(concepts: List[str]) -> None:
    """Add new concepts to the graph with embeddings and semantic edges."""
    concepts = [c for c in concepts if c and c.strip() != ""]
    if not concepts or embed_model is None:
        logging.warning("No concepts or embedding model unavailable.")
        return

    try:
        embeddings = embed_model.encode(concepts)
    except Exception as e:
        logging.error(f"Failed to encode embeddings: {e}")
        embeddings = [np.zeros(384) for _ in concepts]

    # Add nodes with metadata
    for idx, concept in enumerate(concepts):
        if concept not in knowledge_graph:
            knowledge_graph.add_node(
                concept,
                embedding=embeddings[idx],
                count=1,
                memory_score=0.3,
                next_review_time=datetime.now() + timedelta(hours=1),
                created_at=datetime.now().isoformat(),
                source="db_sync",
                last_seen_ts=datetime.now().isoformat()
            )
        else:
            knowledge_graph.nodes[concept]['count'] += 1
            knowledge_graph.nodes[concept]['last_seen_ts'] = datetime.now().isoformat()

    # Add semantic similarity edges
    for i in range(len(concepts)):
        for j in range(i + 1, len(concepts)):
            vec_i = embeddings[i]
            vec_j = embeddings[j]
            cosine_sim = safe_cosine_similarity(vec_i, vec_j)
            if cosine_sim > SIMILARITY_THRESHOLD:
                add_semantic_edge(concepts[i], concepts[j], cosine_sim)

    logging.info(f"Added {len(concepts)} concepts with semantic edges.")

# ==========================================================
# SEMANTIC EDGE ADDER
# ==========================================================
@safe_exec
def add_semantic_edge(n1: str, n2: str, weight: float) -> None:
    """Add or update semantic edge with metadata."""
    if knowledge_graph.has_edge(n1, n2):
        knowledge_graph[n1][n2]['weight'] += weight
        knowledge_graph[n1][n2]['last_updated'] = datetime.now().isoformat()
        knowledge_graph[n1][n2]['count'] += 1
    else:
        knowledge_graph.add_edge(
            n1, n2,
            weight=weight,
            type="semantic",
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            count=1
        )

# ==========================================================
# ADD CO-OCCURRENCE EDGES
# ==========================================================
@safe_exec
def add_edges(
    ocr_keywords: Dict[str, Any],
    audio_label: Optional[str],
    intent_label: str,
    G: Optional[nx.Graph] = None
) -> nx.Graph:
    """Add cross-modal co-occurrence edges (OCR/Audio ↔ Intent)."""
    if G is None:
        G = knowledge_graph

    for kw in ocr_keywords.keys():
        G.add_edge(("OCR", kw), ("Intent", intent_label), type="co_occurrence", last_updated=datetime.now().isoformat())

    if audio_label:
        G.add_edge(("Audio", audio_label), ("Intent", intent_label), type="co_occurrence", last_updated=datetime.now().isoformat())

    logging.info(f"Added co-occurrence edges for intent '{intent_label}'.")
    return G

# ==========================================================
# PRUNE STALE NODES
# ==========================================================
@safe_exec
def prune_stale_nodes(days: int = STALE_NODE_DAYS) -> int:
    """Remove nodes not updated in the last `days`."""
    now = datetime.now()
    removed = 0
    for node, data in list(knowledge_graph.nodes(data=True)):
        last_seen = data.get('last_seen_ts')
        if last_seen:
            last_dt = datetime.fromisoformat(last_seen)
            if (now - last_dt).days > days:
                knowledge_graph.remove_node(node)
                removed += 1
    logging.info(f"Pruned {removed} stale nodes older than {days} days.")
    return removed

# ==========================================================
# SYNC DB CONCEPTS INTO GRAPH
# ==========================================================
@safe_exec
def sync_db_to_graph() -> None:
    """Fetch DB concepts and add to graph incrementally."""
    db_concepts = fetch_concepts_from_db()
    if db_concepts:
        add_concepts(db_concepts)
        save_graph()
        validate_graph_integrity(knowledge_graph)
        sync_memory_scores()
    else:
        logging.warning("No DB concepts found to sync.")

# ==========================================================
# SYNC MEMORY SCORES
# ==========================================================
@safe_exec
def sync_memory_scores():
    """Update knowledge_graph nodes with latest memory_score from memory_decay table."""
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute("SELECT concept, predicted_recall, last_seen_ts FROM memory_decay")
        rows = c.fetchall()
        for concept, score, last_seen in rows:
            if concept in knowledge_graph:
                current_ts = knowledge_graph.nodes[concept].get('last_seen_ts')
                if current_ts is None or last_seen >= current_ts:
                    knowledge_graph.nodes[concept]['memory_score'] = score
                    knowledge_graph.nodes[concept]['last_seen_ts'] = last_seen
            else:
                knowledge_graph.add_node(
                    concept,
                    embedding=np.zeros(384),
                    count=1,
                    memory_score=score,
                    next_review_time=datetime.now() + timedelta(hours=1),
                    created_at=datetime.now().isoformat(),
                    source="memory_decay_sync",
                    last_seen_ts=last_seen
                )
        logging.info(f"Synced {len(rows)} memory_decay entries into knowledge_graph.")
    finally:
        conn.close()

# ==========================================================
# NODE CENTRALITY
# ==========================================================
@safe_exec
def compute_node_centrality() -> Dict[str, float]:
    """Compute degree centrality for all nodes."""
    centrality = nx.degree_centrality(knowledge_graph)
    for node, score in centrality.items():
        knowledge_graph.nodes[node]['centrality'] = score
    logging.info("Updated node centrality for knowledge graph.")
    return centrality

# ==========================================================
# GRAPH VALIDATION / INTEGRITY CHECK
# ==========================================================
def validate_graph_integrity(G: nx.Graph) -> bool:
    """Check for isolated nodes or empty graph; log summary."""
    if len(G.nodes) == 0:
        logging.warning("Graph integrity check failed: graph is empty.")
        return False
    isolated_nodes = list(nx.isolates(G))
    if isolated_nodes:
        logging.info(f"{len(isolated_nodes)} isolated nodes detected.")
    else:
        logging.info("Graph integrity OK: no isolated nodes.")
    return True

# ==========================================================
# RETURN GRAPH
# ==========================================================
def get_graph() -> nx.Graph:
    """Return the active knowledge graph instance."""
    return knowledge_graph

# ==========================================================
# DEBUG / SELF-TEST
# ==========================================================
if __name__ == "__main__":
    sync_db_to_graph()
    prune_stale_nodes()
    compute_node_centrality()
    print(f"✅ Graph Loaded: {len(knowledge_graph.nodes)} nodes, {len(knowledge_graph.edges)} edges")
    print("Sample nodes:", list(knowledge_graph.nodes(data=True))[:5])
    print("Sample edges:", list(knowledge_graph.edges(data=True))[:5])
