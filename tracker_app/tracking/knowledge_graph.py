# core/knowledge_graph.py
# FKT 2.0 — Fixed knowledge graph.
# Changes from v1:
#   1. SentenceTransformer is lazy-loaded (not at import time) — fixes OOM crash
#   2. fetch_concepts_from_db() now reads tracked_concepts, NOT window titles
#   3. Embeddings are optional — graph works with spaCy vectors as fallback
import networkx as nx
import numpy as np
import sqlite3
import threading
import logging
from datetime import datetime, timedelta
from tracker_app.config import DB_PATH

logger = logging.getLogger("KnowledgeGraph")

# Consistent datetime format across all modules
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Thread safety lock for graph operations
_graph_lock = threading.RLock()

# ----------------------------
# Lazy embedding model
# ----------------------------
_embed_model = None

def _get_embed_model():
    """Lazily load SentenceTransformer only when actually needed."""
    global _embed_model
    if _embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embed_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("SentenceTransformer loaded for knowledge graph.")
        except Exception as e:
            logger.warning(f"SentenceTransformer unavailable ({e}). Falling back to spaCy vectors.")
            _embed_model = None
    return _embed_model

def _get_spacy_vectors(concepts):
    """Fallback: use spaCy word vectors for similarity."""
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        return np.array([nlp(c).vector for c in concepts])
    except Exception as e:
        logger.warning(f"spaCy vector fallback failed: {e}")
        return None

# Create the main knowledge graph
knowledge_graph = nx.Graph()

def fetch_concepts_from_db():
    """Fetch concepts from tracked_concepts table (NOT window titles)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # FKT 2.0 fix: read actual tracked concepts, not OS window titles
        c.execute("SELECT DISTINCT concept FROM tracked_concepts WHERE concept IS NOT NULL")
        rows = c.fetchall()
        conn.close()
        concepts = [row[0].strip() for row in rows if row[0] and row[0].strip()]
        return concepts
    except Exception as e:
        logger.error(f"Error fetching concepts from DB: {e}")
        return []

def add_concepts(concepts):
    """
    Add concepts to the graph and connect semantically similar nodes.
    Thread-safe. Uses lazy-loaded embeddings with spaCy fallback.
    """
    if not concepts:
        return

    valid_concepts = [str(c).strip() for c in concepts if c and str(c).strip()]
    if not valid_concepts:
        return

    # Try to get embeddings — optional, graceful fallback
    embeddings = None
    embed_model = _get_embed_model()
    if embed_model is not None:
        try:
            embeddings = embed_model.encode(valid_concepts)
        except Exception as e:
            logger.warning(f"SentenceTransformer encode failed: {e}")
            embeddings = None

    if embeddings is None:
        embeddings = _get_spacy_vectors(valid_concepts)

    with _graph_lock:
        for idx, concept in enumerate(valid_concepts):
            if concept not in knowledge_graph:
                knowledge_graph.add_node(
                    concept,
                    embedding=embeddings[idx].tolist() if embeddings is not None else [],
                    count=1,
                    memory_score=0.3,
                    next_review_time=datetime.now().strftime(DATETIME_FORMAT),
                    last_review=datetime.now().strftime(DATETIME_FORMAT),
                    intent_conf=1.0
                )
            else:
                knowledge_graph.nodes[concept]['count'] += 1

        # Add semantic edges only when embeddings are available
        if embeddings is not None:
            for i in range(len(valid_concepts)):
                for j in range(i + 1, len(valid_concepts)):
                    try:
                        vec_i = embeddings[i]
                        vec_j = embeddings[j]
                        norm_i = np.linalg.norm(vec_i)
                        norm_j = np.linalg.norm(vec_j)
                        if norm_i == 0 or norm_j == 0:
                            continue
                        cosine_sim = np.dot(vec_i, vec_j) / (norm_i * norm_j)
                        if cosine_sim > 0.7:
                            if knowledge_graph.has_edge(valid_concepts[i], valid_concepts[j]):
                                knowledge_graph[valid_concepts[i]][valid_concepts[j]]['weight'] += cosine_sim
                            else:
                                knowledge_graph.add_edge(valid_concepts[i], valid_concepts[j], weight=cosine_sim)
                    except Exception as e:
                        logger.warning(f"Error adding edge between concepts: {e}")

def sync_db_to_graph():
    """Synchronize database concepts to graph"""
    try:
        db_concepts = fetch_concepts_from_db()
        add_concepts(db_concepts)
        print(f"Synced {len(db_concepts)} concepts from DB to graph")
    except Exception as e:
        print(f"Error syncing DB to graph: {e}")

def get_graph():
    """Get graph with thread-safe access"""
    return knowledge_graph

def add_edges(ocr_keywords, audio_label, intent_label, G=None):
    """Add edges between different modalities - thread-safe"""
    if G is None:
        G = get_graph()

    try:
        with _graph_lock:
            if ocr_keywords and isinstance(ocr_keywords, dict):
                for kw in ocr_keywords.keys():
                    if kw and str(kw).strip():
                        G.add_edge(("OCR", str(kw)), ("Intent", str(intent_label)), type="co_occurrence")
            
            if audio_label and str(audio_label).strip():
                G.add_edge(("Audio", str(audio_label)), ("Intent", str(intent_label)), type="co_occurrence")

        return G
    except Exception as e:
        print(f"Error adding edges: {e}")
        return G

if __name__ == "__main__":
    sync_db_to_graph()
    print("Nodes with attributes:")
    for node, data in list(knowledge_graph.nodes(data=True))[:5]:
        print(f"  {node}: {data}")
    print("\nEdges with weights:")
    for edge in list(knowledge_graph.edges(data=True))[:5]:
        print(f"  {edge}")