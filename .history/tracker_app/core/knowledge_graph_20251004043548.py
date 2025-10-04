#core/knowledge_graph.py
import networkx as nx
from sentence_transformers import SentenceTransformer
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH # make sure this path points to your DB

# Initialize embedding model
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

# Create the main knowledge graph
knowledge_graph = nx.Graph()

# ------------------------------
# Helper: Fetch concepts from DB
# ------------------------------
def fetch_concepts_from_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT window_title FROM sessions")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

# ------------------------------
# Add concepts and semantic edges
# ------------------------------
def add_concepts(concepts):
    """
    Add concepts to the graph and connect semantically similar nodes.
    If DB info exists, attach memory score and next_review.
    """
    # Compute embeddings
    embeddings = embed_model.encode(concepts)

    for idx, concept in enumerate(concepts):
        if concept not in knowledge_graph:
            # Default memory info
            knowledge_graph.add_node(
                concept,
                embedding=embeddings[idx],
                count=1,
                memory_score=0.3,  # default if not calculated
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

# ------------------------------
# Sync DB concepts into graph
# ------------------------------
def sync_db_to_graph():
    db_concepts = fetch_concepts_from_db()
    add_concepts(db_concepts)

# ------------------------------
# Return graph
# ------------------------------
def get_graph():
    return knowledge_graph

def add_edges(ocr_keywords, audio_label, intent_label, G=None):
    if G is None:
        G = get_graph()

    for kw in ocr_keywords.keys():
        G.add_edge(("OCR", kw), ("Intent", intent_label), type="co_occurrence")
    if audio_label:
        G.add_edge(("Audio", audio_label), ("Intent", intent_label), type="co_occurrence")

    return G

# ------------------------------
# Example usage
# ------------------------------
if __name__ == "__main__":
    sync_db_to_graph()
    print("Nodes with attributes:")
    print(knowledge_graph.nodes(data=True))
    print("\nEdges with weights:")
    print(knowledge_graph.edges(data=True))
