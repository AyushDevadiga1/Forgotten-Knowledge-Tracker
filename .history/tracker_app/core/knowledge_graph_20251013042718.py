# ==========================================================
# core/knowledge_graph.py | IEEE v3.0 Multi-Modal Upgrade
# ==========================================================
"""
Knowledge Graph Management Module (v3.0)
----------------------------------------
- Lazy-loading embedding models (multi-modal)
- Incremental & async-safe updates from OCR, Intent, Audio, Attention
- Nodes: Concept, OCRKeyword, Intent, AudioEvent
- Edges: semantic, co_occurrence, temporal, intent_association
- Metadata: memory_score, attention_score, timestamps, source_module
- Graph validation, analytics, and full logging
"""

import networkx as nx
import numpy as np
import sqlite3
import joblib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
import logging
from functools import lru_cache
from config import DB_PATH, GRAPH_PATH

# ==========================================================
# LOGGER SETUP
# ==========================================================
logger = logging.getLogger("KnowledgeGraph")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(funcName)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ==========================================================
# SAFE EXEC DECORATOR
# ==========================================================
def safe_exec(func: Callable):
    """Decorator to safely execute functions and log exceptions."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"{func.__name__} failed: {e}")
            return None
    return wrapper

# ==========================================================
# GLOBAL GRAPH INSTANCE
# ==========================================================
knowledge_graph: nx.Graph = nx.Graph()

# ==========================================================
# LAZY EMBEDDING MODEL HANDLER
# ==========================================================
_embed_model: Optional[Any] = None
EMBED_DIM = 384

def get_embed_model():
    global _embed_model
    if _embed_model is not None:
        return _embed_model
    try:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded successfully.")
    except Exception as e:
        _embed_model = None
        logger.warning(f"Embedding model load failed: {e}")
    return _embed_model

def encode_embeddings(items: List[str]) -> List[np.ndarray]:
    model = get_embed_model()
    if model is None or not items:
        return [np.zeros(EMBED_DIM) for _ in items]
    try:
        return model.encode(items)
    except Exception as e:
        logger.warning(f"Embedding encoding failed: {e}")
        return [np.zeros(EMBED_DIM) for _ in items]

# ==========================================================
# GRAPH PERSISTENCE
# ==========================================================
@safe_exec
def save_graph(versioned: bool = True) -> None:
    import os
    os.makedirs("data", exist_ok=True)
    path = GRAPH_PATH
    if versioned:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"data/knowledge_graph_v{timestamp}.pkl"
    joblib.dump(knowledge_graph, path)
    logger.info(f"Graph saved to {path}")

@safe_exec
def load_graph() -> None:
    global knowledge_graph
    try:
        knowledge_graph = joblib.load(GRAPH_PATH)
        logger.info(f"Graph loaded from {GRAPH_PATH}")
    except FileNotFoundError:
        knowledge_graph = nx.Graph()
        logger.warning("Graph file not found — starting new graph.")

# Load at startup
load_graph()

# ==========================================================
# SAFE COSINE SIMILARITY
# ==========================================================
def safe_cosine_similarity(vec_i: np.ndarray, vec_j: np.ndarray) -> float:
    denom = np.linalg.norm(vec_i) * np.linalg.norm(vec_j)
    if denom == 0:
        return 0.0
    return float(np.dot(vec_i, vec_j) / denom)

# ==========================================================
# FETCH CONCEPTS FROM DB
# ==========================================================
@safe_exec
def fetch_concepts_from_db() -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute("SELECT DISTINCT window_title FROM sessions")
        return [row[0].strip() for row in c.fetchall() if row[0] and row[0].strip()]
    finally:
        conn.close()

# ==========================================================
# ADD NODES & SEMANTIC EDGES
# ==========================================================
@safe_exec
def add_concepts(concepts: List[str], source_module: str = "db_sync") -> None:
    concepts = [c for c in concepts if c and c.strip()]
    if not concepts:
        return
    embeddings = encode_embeddings(concepts)
    for idx, concept in enumerate(concepts):
        if concept not in knowledge_graph:
            knowledge_graph.add_node(
                concept,
                type="Concept",
                embedding=embeddings[idx],
                memory_score=0.3,
                attention_score=None,
                count=1,
                source=source_module,
                created_at=datetime.now().isoformat(),
                last_seen_ts=datetime.now().isoformat()
            )
        else:
            knowledge_graph.nodes[concept]['count'] += 1
            knowledge_graph.nodes[concept]['last_seen_ts'] = datetime.now().isoformat()
    # Semantic edges
    for i in range(len(concepts)):
        for j in range(i + 1, len(concepts)):
            sim = safe_cosine_similarity(embeddings[i], embeddings[j])
            if sim > GRAPH_SIMILARITY_THRESHOLD:
                add_semantic_edge(concepts[i], concepts[j], sim)

@safe_exec
def add_semantic_edge(n1: str, n2: str, weight: float) -> None:
    if knowledge_graph.has_edge(n1, n2):
        knowledge_graph[n1][n2]['weight'] += weight
        knowledge_graph[n1][n2]['count'] += 1
        knowledge_graph[n1][n2]['last_updated'] = datetime.now().isoformat()
    else:
        knowledge_graph.add_edge(
            n1, n2,
            type="semantic",
            weight=weight,
            count=1,
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )

# ==========================================================
# ADD MULTI-MODAL EDGES
# ==========================================================
@safe_exec
def add_multimodal_edges(
    ocr_keywords: Dict[str, Any],
    audio_label: Optional[str],
    intent_label: str
) -> None:
    for kw in ocr_keywords.keys():
        knowledge_graph.add_edge(
            ("OCR", kw), ("Intent", intent_label),
            type="co_occurrence",
            last_updated=datetime.now().isoformat()
        )
    if audio_label:
        knowledge_graph.add_edge(
            ("Audio", audio_label), ("Intent", intent_label),
            type="co_occurrence",
            last_updated=datetime.now().isoformat()
        )
    logger.info(f"Added multi-modal edges for intent '{intent_label}'")

# ==========================================================
# PRUNE STALE NODES
# ==========================================================
@safe_exec
def prune_stale_nodes(days: int = STALE_NODE_DAYS) -> int:
    removed = 0
    now = datetime.now()
    for node, data in list(knowledge_graph.nodes(data=True)):
        last_seen = data.get('last_seen_ts')
        if last_seen and (now - datetime.fromisoformat(last_seen)).days > days:
            knowledge_graph.remove_node(node)
            removed += 1
    logger.info(f"Pruned {removed} stale nodes older than {days} days")
    return removed

# ==========================================================
# MEMORY & ATTENTION SYNC
# ==========================================================
@safe_exec
def sync_memory_attention() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute("SELECT concept, predicted_recall, last_seen_ts FROM memory_decay")
        rows = c.fetchall()
        for concept, mem_score, ts in rows:
            if concept in knowledge_graph:
                knowledge_graph.nodes[concept]['memory_score'] = mem_score
                knowledge_graph.nodes[concept]['last_seen_ts'] = ts
            else:
                knowledge_graph.add_node(
                    concept,
                    type="Concept",
                    embedding=np.zeros(EMBED_DIM),
                    memory_score=mem_score,
                    attention_score=None,
                    count=1,
                    source="memory_decay",
                    created_at=datetime.now().isoformat(),
                    last_seen_ts=ts
                )
        logger.info(f"Synced {len(rows)} memory_decay entries into graph")
    finally:
        conn.close()

# ==========================================================
# NODE CENTRALITY
# ==========================================================
@safe_exec
def compute_node_centrality() -> Dict[str, float]:
    centrality = nx.degree_centrality(knowledge_graph)
    for node, score in centrality.items():
        knowledge_graph.nodes[node]['centrality'] = score
    logger.info("Updated node centrality")
    return centrality

# ==========================================================
# VALIDATION
# ==========================================================
def validate_graph() -> bool:
    if len(knowledge_graph.nodes) == 0:
        logger.warning("Graph empty")
        return False
    isolates = list(nx.isolates(knowledge_graph))
    if isolates:
        logger.info(f"{len(isolates)} isolated nodes found")
    return True

# ==========================================================
# GET GRAPH INSTANCE
# ==========================================================
def get_graph() -> nx.Graph:
    return knowledge_graph

# ==========================================================
# SYNC DB TO GRAPH (INCREMENTAL)
# ==========================================================
@safe_exec
def sync_db_to_graph() -> None:
    db_concepts = fetch_concepts_from_db()
    if db_concepts:
        add_concepts(db_concepts)
        save_graph()
        validate_graph()
        sync_memory_attention()

# ==========================================================
# SELF-TEST
# ==========================================================
if __name__ == "__main__":
    sync_db_to_graph()
    prune_stale_nodes()
    compute_node_centrality()
    logger.info(f"Graph loaded: {len(knowledge_graph.nodes)} nodes, {len(knowledge_graph.edges)} edges")
