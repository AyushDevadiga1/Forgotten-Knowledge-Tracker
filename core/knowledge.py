# Phase 6: knowledge graph
import sqlite3
import networkx as nx
from sentence_transformers import SentenceTransformer
from config import DB_PATH
import numpy as np

# Load lightweight embedding model
model_path = r"C:\Users\hp\Desktop\FKT\models\all-MiniLM-L6-v2"
model = SentenceTransformer(model_path)

def fetch_keywords():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, keywords FROM ocr_logs ORDER BY id DESC LIMIT 50")  # last 50 entries
    rows = cur.fetchall()
    conn.close()
    return rows

def build_knowledge_graph():
    G = nx.Graph()
    data = fetch_keywords()
    
    for entry_id, keywords_str in data:
        keywords = [k.strip() for k in keywords_str.split(',')]
        for k in keywords:
            if not G.has_node(k):
                G.add_node(k)
    
    # Compute edges based on semantic similarity
    all_keywords = list(G.nodes)
    embeddings = model.encode(all_keywords)
    
    for i in range(len(all_keywords)):
        for j in range(i + 1, len(all_keywords)):
            sim = cosine_similarity(embeddings[i], embeddings[j])
            if sim > 0.6:  # threshold
                G.add_edge(all_keywords[i], all_keywords[j], weight=sim)
    
    return G

def cosine_similarity(vec1, vec2):
    import numpy as np
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def print_graph_summary(G):
    print(f"[Knowledge Graph] Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
