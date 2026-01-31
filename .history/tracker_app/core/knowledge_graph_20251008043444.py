"""
Knowledge Graph Management Module (IEEE v2.1)
---------------------------------------------
- Builds and maintains a semantic graph of concepts.
- Computes embeddings and semantic similarity edges.
- Syncs DB sessions/concepts into the graph.
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
def save_graph() -> None:
    """Save the current knowledge graph to disk."""
    joblib.dump(knowledge_graph, GRAPH_PATH)
    logging.info(f"Knowledge graph saved to {GRAPH_PATH}")

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
    c = conn.cursor()
    c.execute("SELECT DISTINCT window_title FROM sessions")
    rows = c.fetchall()
    conn.close()

    concepts = [row[0].strip() for row in rows if row[0] and row[0].strip()]
    logging.info(f"Fetched {len(concepts)} concepts from DB.")
    return concepts

# ==========================================================
# ADD CONCEPTS AND SEMANTIC EDGES
# ==========================================================
@safe_exec
def add_concepts(concepts: List[str]) -> None:
    """
    Add new concepts to the graph and connect semantically similar nodes.
    Adds IEEE-grade metadata for traceability.
    """
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
                memory_score=0.3,  # default base
                next_review_time=datetime.now() + timedelta(hours=1),
                created_at=datetime.now().isoformat(),
                source="db_sync"
            )
        else:
            knowledge_graph.nodes[concept]['count'] += 1

    # Add semantic similarity edges
    for i in range(len(concepts)):
        for j in range(i + 1, len(concepts)):
            vec_i = embeddings[i]
            vec_j = embeddings[j]
            cosine_sim = safe_cosine_similarity(vec_i, vec_j)
            if cosine_sim > 0.7:
                if knowledge_graph.has_edge(concepts[i], concepts[j]):
                    knowledge_graph[concepts[i]][concepts[j]]['weight'] += cosine_sim
                else:
                    knowledge_graph.add_edge(concepts[i], concepts[j], weight=cosine_sim)

    logging.info(f"Added {len(concepts)} concepts with semantic edges.")

# ==========================================================
# SYNC DB CONCEPTS INTO GRAPH
# ==========================================================
@safe_exec
def sync_db_to_graph() -> None:
    """Fetch DB concepts and add to graph."""
    db_concepts = fetch_concepts_from_db()
    if db_concepts:
        add_concepts(db_concepts)
        save_graph()
        validate_graph_integrity(knowledge_graph)
    else:
        logging.warning("No DB concepts found to sync.")
        
@safe_exec
def sync_memory_scores():
    """
    Update knowledge_graph nodes with the latest memory_score
    from the memory_decay table.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute("SELECT concept, predicted_recall, last_seen_ts FROM memory_decay")
        rows = c.fetchall()
        for concept, score, last_seen in rows:
            if concept in knowledge_graph:
                knowledge_graph.nodes[concept]['memory_score'] = score
                knowledge_graph.nodes[concept]['last_seen_ts'] = last_seen
            else:
                # Optionally add new concept if not in graph
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
# RETURN GRAPH
# ==========================================================
def get_graph() -> nx.Graph:
    """Return the active knowledge graph instance."""
    return knowledge_graph

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
        G = get_graph()

    for kw in ocr_keywords.keys():
        G.add_edge(("OCR", kw), ("Intent", intent_label), type="co_occurrence")

    if audio_label:
        G.add_edge(("Audio", audio_label), ("Intent", intent_label), type="co_occurrence")

    logging.info(f"Added co-occurrence edges for intent '{intent_label}'.")
    return G

# ==========================================================
# VALIDATION / INTEGRITY CHECK
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
# EXAMPLE EXECUTION (DEBUG MODE)
# ==========================================================
if __name__ == "__main__":
    sync_db_to_graph()
    print(f"✅ Graph Loaded: {len(knowledge_graph.nodes)} nodes, {len(knowledge_graph.edges)} edges")
    print("Sample nodes:", list(knowledge_graph.nodes(data=True))[:5])
    print("Sample edges:", list(knowledge_graph.edges(data=True))[:5])
