# core/knowledge_graph.py
import networkx as nx
from sentence_transformers import SentenceTransformer
import numpy as np
import sqlite3
import json
import threading
from datetime import datetime, timedelta
from config import DB_PATH

# Consistent datetime format across all modules
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Thread safety lock for graph operations
_graph_lock = threading.RLock()

# Initialize embedding model
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

# Create the main knowledge graph
knowledge_graph = nx.Graph()

def fetch_concepts_from_db():
    """Fetch concepts from database safely"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT DISTINCT window_title FROM sessions WHERE window_title IS NOT NULL")
        rows = c.fetchall()
        conn.close()
        
        # Keep only non-empty strings
        concepts = [row[0].strip() for row in rows if row[0] and row[0].strip()]
        return concepts
    except Exception as e:
        print(f"Error fetching concepts from DB: {e}")
        return []

def add_concepts(concepts):
    """
    Add concepts to the graph and connect semantically similar nodes.
    Thread-safe with locking.
    """
    if not concepts:
        return

    # Filter and validate concepts
    valid_concepts = [str(c).strip() for c in concepts if c and str(c).strip()]
    if not valid_concepts:
        return

    try:
        # Compute embeddings
        embeddings = embed_model.encode(valid_concepts)
    except Exception as e:
        print(f"Error computing embeddings: {e}")
        return

    with _graph_lock:
        for idx, concept in enumerate(valid_concepts):
            if concept not in knowledge_graph:
                # Default memory info - use consistent datetime format
                knowledge_graph.add_node(
                    concept,
                    embedding=embeddings[idx],
                    count=1,
                    memory_score=0.3,
                    next_review_time=datetime.now().strftime(DATETIME_FORMAT),
                    last_review=datetime.now().strftime(DATETIME_FORMAT),
                    intent_conf=1.0
                )
            else:
                knowledge_graph.nodes[concept]['count'] += 1

        # Add semantic edges
        for i in range(len(valid_concepts)):
            for j in range(i + 1, len(valid_concepts)):
                try:
                    vec_i = embeddings[i]
                    vec_j = embeddings[j]
                    cosine_sim = np.dot(vec_i, vec_j) / (np.linalg.norm(vec_i) * np.linalg.norm(vec_j))
                    if cosine_sim > 0.7:
                        if knowledge_graph.has_edge(valid_concepts[i], valid_concepts[j]):
                            knowledge_graph[valid_concepts[i]][valid_concepts[j]]['weight'] += cosine_sim
                        else:
                            knowledge_graph.add_edge(valid_concepts[i], valid_concepts[j], weight=cosine_sim)
                except Exception as e:
                    print(f"Error adding edge between {valid_concepts[i]} and {valid_concepts[j]}: {e}")

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