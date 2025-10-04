import networkx as nx
from sentence_transformers import SentenceTransformer
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH
from core.sm2_scheduler import sm2_scheduler  # NEW

# Initialize embedding model - ORIGINAL
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

# Create the main knowledge graph - ORIGINAL
knowledge_graph = nx.Graph()

# ------------------------------
# Helper: Fetch concepts from DB - ORIGINAL
# ------------------------------
def fetch_concepts_from_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT window_title FROM sessions")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

# NEW: Enhanced concept fetching
def fetch_enhanced_concepts_from_db():
    """Fetch concepts from enhanced sessions table"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get keywords from enhanced sessions
    c.execute("SELECT keywords FROM sessions_enhanced WHERE keywords IS NOT NULL")
    rows = c.fetchall()
    
    concepts = set()
    for row in rows:
        if row[0]:
            try:
                # Keywords are stored as string representation of list
                import ast
                keywords = ast.literal_eval(row[0])
                concepts.update(keywords)
            except:
                continue
    
    conn.close()
    return list(concepts)

# ------------------------------
# Add concepts and semantic edges - ORIGINAL (PRESERVED)
# ------------------------------
def add_concepts(concepts):
    """
    ORIGINAL: Add concepts to the graph and connect semantically similar nodes.
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
                memory_score=0.3,
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

# NEW: Enhanced concept addition with SM-2
def add_concepts_enhanced(concepts, ocr_confidence=0.5, audio_confidence=0.5, 
                         attention_score=50, interaction_rate=0, app_type="unknown"):
    """
    Enhanced concept addition with SM-2 scheduling
    """
    # Compute embeddings
    embeddings = embed_model.encode(concepts)

    for idx, concept in enumerate(concepts):
        if concept not in knowledge_graph:
            # Initialize with SM-2 scheduling
            quality = sm2_scheduler.map_confidence_to_quality(
                ocr_confidence, audio_confidence, attention_score, interaction_rate, app_type
            )
            
            sm2_data = sm2_scheduler.calculate_next_review(quality=quality)
            
            knowledge_graph.add_node(
                concept,
                embedding=embeddings[idx],
                count=1,
                memory_score=sm2_data['memory_score'] if 'memory_score' in sm2_data else 0.3,
                next_review_time=sm2_data['next_review'],
                interval=sm2_data['interval'],
                ease_factor=sm2_data['ease_factor'],
                repetitions=sm2_data['repetitions'],
                last_review_time=datetime.now(),
                quality=quality,
                ocr_confidence=ocr_confidence,
                audio_confidence=audio_confidence,
                attention_score=attention_score,
                interaction_rate=interaction_rate,
                app_type=app_type
            )
        else:
            # Update existing concept
            knowledge_graph.nodes[concept]['count'] += 1
            
            # Update with new context information
            knowledge_graph.nodes[concept]['ocr_confidence'] = ocr_confidence
            knowledge_graph.nodes[concept]['audio_confidence'] = audio_confidence
            knowledge_graph.nodes[concept]['attention_score'] = attention_score
            knowledge_graph.nodes[concept]['interaction_rate'] = interaction_rate
            knowledge_graph.nodes[concept]['app_type'] = app_type

    # Add semantic edges (same as original)
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
# Sync DB concepts into graph - ORIGINAL
# ------------------------------
def sync_db_to_graph():
    db_concepts = fetch_concepts_from_db()
    add_concepts(db_concepts)

# NEW: Enhanced sync with SM-2 data
def sync_db_to_graph_enhanced():
    """Enhanced sync with concepts from enhanced sessions"""
    db_concepts = fetch_enhanced_concepts_from_db()
    
    if db_concepts:
        # Use enhanced addition for better scheduling
        add_concepts_enhanced(db_concepts)
    else:
        # Fallback to original sync
        sync_db_to_graph()

# ------------------------------
# Return graph - ORIGINAL
# ------------------------------
def get_graph():
    return knowledge_graph

# NEW: Graph analysis functions
def get_graph_statistics():
    """Get statistics about the knowledge graph"""
    G = get_graph()
    
    if len(G.nodes) == 0:
        return {
            'node_count': 0,
            'edge_count': 0,
            'avg_memory_score': 0,
            'concepts_due_review': 0
        }
    
    memory_scores = [G.nodes[node].get('memory_score', 0.3) for node in G.nodes]
    now = datetime.now()
    
    concepts_due = 0
    for node in G.nodes:
        next_review = G.nodes[node].get('next_review_time', now)
        if isinstance(next_review, str):
            next_review = datetime.fromisoformat(next_review)
        if next_review <= now:
            concepts_due += 1
    
    return {
        'node_count': len(G.nodes),
        'edge_count': len(G.edges),
        'avg_memory_score': sum(memory_scores) / len(memory_scores),
        'concepts_due_review': concepts_due,
        'avg_degree': sum(dict(G.degree()).values()) / len(G.nodes) if G.nodes else 0
    }

# NEW: Concept clustering
def cluster_similar_concepts(threshold=0.8):
    """Cluster similar concepts based on embeddings"""
    G = get_graph()
    if len(G.nodes) < 2:
        return []
    
    # Get all embeddings
    concepts = list(G.nodes)
    embeddings = np.array([G.nodes[concept]['embedding'] for concept in concepts])
    
    # Calculate similarity matrix
    from sklearn.metrics.pairwise import cosine_similarity
    similarity_matrix = cosine_similarity(embeddings)
    
    # Find clusters
    clusters = []
    visited = set()
    
    for i, concept1 in enumerate(concepts):
        if concept1 in visited:
            continue
            
        cluster = [concept1]
        visited.add(concept1)
        
        for j, concept2 in enumerate(concepts):
            if i != j and concept2 not in visited and similarity_matrix[i][j] > threshold:
                cluster.append(concept2)
                visited.add(concept2)
        
        if len(cluster) > 1:
            clusters.append(cluster)
    
    return clusters

# ------------------------------
# Example usage - ORIGINAL
# ------------------------------
if __name__ == "__main__":
    print("Testing original sync:")
    sync_db_to_graph()
    print("Nodes with attributes:")
    print(knowledge_graph.nodes(data=True))
    
    print("\nTesting enhanced sync:")
    sync_db_to_graph_enhanced()
    
    print("\nGraph statistics:")
    stats = get_graph_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print("\nSimilar concept clusters:")
    clusters = cluster_similar_concepts()
    for i, cluster in enumerate(clusters):
        print(f"Cluster {i+1}: {cluster}")