# core/knowledge_graph.py
"""
Knowledge Graph Management Module
---------------------------------
- Builds and maintains a semantic graph of concepts.
- Computes embeddings, adds semantic edges.
- Syncs DB sessions/concepts into the graph.
- Fully typed and traceable for IEEE-grade logging.
"""

import networkx as nx
from sentence_transformers import SentenceTransformer
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
from config import DB_PATH

# -----------------------------
# LOGGER SETUP
# -----------------------------
logging.basicConfig(
    filename="logs/knowledge_graph.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -----------------------------
# Initialize embedding model
# -----------------------------
try:
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    logging.error(f"Failed to load embedding model: {e}")
    embed_model = None

# -----------------------------
# Initialize main knowledge graph
# -----------------------------
knowledge_graph: nx.Graph = nx.Graph()

# -----------------------------
# Helper: Fetch concepts from DB
# -----------------------------
def fetch_concepts_from_db() -> List[str]:
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT DISTINCT window_title FROM sessions")
        rows = c.fetchall()
        conn.close()
        concepts = [row[0].strip() for row in rows if row[0] and row[0].strip()]
        logging.info(f"Fetched {len(concepts)} concepts from DB")
        return concepts
    except Exception as e:
        logging.error(f"Failed to fetch concepts from DB: {e}")
        return []

# -----------------------------
# Add concepts and semantic edges
# -----------------------------
def add_concepts(concepts: List[str]) -> None:
    """
    Add concepts to the graph and connect semantically similar nodes.
    If DB info exists, attach memory score and next_review.
    """
    concepts = [c for c in concepts if c and c.strip() != ""]
    if not concepts or embed_model is None:
        return

    try:
        embeddings = embed_model.encode(concepts)
    except Exception as e:
        logging.error(f"Failed to encode embeddings: {e}")
        embeddings = [np.zeros(384) for _ in concepts]

    for idx, concept in enumerate(concepts):
        if concept not in knowledge_graph:
            knowledge_graph.add_node(
                concept,
                embedding=embeddings[idx],
                count=1,
                memory_score=0.3,  # default
                next_review_time=datetime.now() + timedelta(hours=1)
            )
        else:
            knowledge_graph.nodes[concept]['count'] += 1

    # Add semantic edges
    for i in range(len(concepts)):
        for j in range(i + 1, len(concepts)):
            vec_i = embeddings[i]
            vec_j = embeddings[j]
            cosine_sim = np.dot(vec_i, vec_j) / (np.linalg.norm(vec_i) * np.linalg.norm(vec_j))
            if cosine_sim > 0.7:
                if knowledge_graph.has_edge(concepts[i], concepts[j]):
                    knowledge_graph[concepts[i]][concepts[j]]['weight'] += cosine_sim
                else:
                    knowledge_graph.add_edge(concepts[i], concepts[j], weight=cosine_sim)

# -----------------------------
# Sync DB concepts into graph
# -----------------------------
def sync_db_to_graph() -> None:
    db_concepts = fetch_concepts_from_db()
    add_concepts(db_concepts)

# -----------------------------
# Return graph
# -----------------------------
def get_graph() -> nx.Graph:
    return knowledge_graph

# -----------------------------
# Add co-occurrence edges
# -----------------------------
def add_edges(
    ocr_keywords: Dict[str, Any],
    audio_label: Optional[str],
    intent_label: str,
    G: Optional[nx.Graph] = None
) -> nx.Graph:
    if G is None:
        G = get_graph()

    for kw in ocr_keywords.keys():
        G.add_edge(("OCR", kw), ("Intent", intent_label), type="co_occurrence")
    if audio_label:
        G.add_edge(("Audio", audio_label), ("Intent", intent_label), type="co_occurrence")

    return G

# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    sync_db_to_graph()
    print("Nodes with attributes:")
    print(knowledge_graph.nodes(data=True))
    print("\nEdges with weights:")
    print(knowledge_graph.edges(data=True))
