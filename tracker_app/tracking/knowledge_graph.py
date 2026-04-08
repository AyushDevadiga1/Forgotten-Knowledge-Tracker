# core/knowledge_graph.py
# FKT 2.0 Phase 6 — Knowledge Graph Improvements
# Changes:
#   - Edge weight uses EMA instead of unbounded accumulation
#   - compute_concept_drift(): Jaccard-based cross-session drift detection (novel)
#   - find_knowledge_gaps(): proactive learning path suggestion (novel)
#   - get_graph_stats(): summary stats for dashboard API
#   - add_concepts() refactored to use EMA edge weights
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
                                # EMA instead of unbounded accumulation
                                old = knowledge_graph[valid_concepts[i]][valid_concepts[j]]['weight']
                                knowledge_graph[valid_concepts[i]][valid_concepts[j]]['weight'] = (
                                    min(1.0, 0.85 * old + 0.15 * cosine_sim)
                                )
                            else:
                                knowledge_graph.add_edge(
                                    valid_concepts[i], valid_concepts[j],
                                    weight=cosine_sim
                                )
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


# ─── Phase 6: Concept Drift Detector ─────────────────────────────────────────

def compute_concept_drift(
    concept: str,
    current_session_keywords: list,
) -> dict:
    """
    Detect how much a concept's context has changed vs. its historical neighbourhood.

    Uses Jaccard distance between:
      - current_session_keywords (what co-occurred this session)
      - historical graph neighbours (weighted edges > 0.3)

    Returns:
        {
            'concept': str,
            'drift_score': float,   # 0.0 = same context, 1.0 = completely different
            'status': str,          # 'new'|'evolving'|'stable'|'stagnant'
            'co_concepts_now': list,
            'co_concepts_historic': list,
        }
    """
    with _graph_lock:
        if concept not in knowledge_graph:
            return {
                'concept': concept, 'drift_score': 0.0, 'status': 'new',
                'co_concepts_now': list(current_session_keywords),
                'co_concepts_historic': [],
            }

        current_neighbours = set(
            k for k in current_session_keywords
            if k != concept and isinstance(k, str)
        )
        historic_neighbours = set(
            n for n in knowledge_graph.neighbors(concept)
            if isinstance(n, str) and
            knowledge_graph[concept][n].get('weight', 0) > 0.3
        )

        if not historic_neighbours:
            return {
                'concept': concept, 'drift_score': 0.0, 'status': 'new',
                'co_concepts_now': sorted(current_neighbours),
                'co_concepts_historic': [],
            }

        intersection = len(current_neighbours & historic_neighbours)
        union        = len(current_neighbours | historic_neighbours)
        drift        = 1.0 - (intersection / union) if union > 0 else 0.0

        if not current_neighbours:
            status = 'stagnant'
        elif drift > 0.6:
            status = 'evolving'
        elif drift > 0.2:
            status = 'stable'
        else:
            status = 'stable'

        return {
            'concept':              concept,
            'drift_score':          round(drift, 4),
            'status':               status,
            'co_concepts_now':      sorted(current_neighbours),
            'co_concepts_historic': sorted(historic_neighbours),
        }


# ─── Phase 6: Knowledge Gap Map ──────────────────────────────────────────────

def find_knowledge_gaps(top_k: int = 5) -> list:
    """
    Identify concepts the user probably should know but hasn't encountered.

    Algorithm:
      For every pair (A, B) with a strong edge (weight > 0.5),
      find concepts C in the graph that:
        - are semantically similar to both A and B (spaCy similarity > 0.55)
        - are NOT directly connected to either A or B
      Surface C as a 'knowledge gap' with a score = avg(sim(A,C), sim(B,C)).

    Returns:
        List of dicts sorted by score descending:
        [{'gap_concept': str, 'bridge_concepts': [str, str], 'score': float}]
    """
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
    except Exception as e:
        logger.warning(f"find_knowledge_gaps: spaCy unavailable — {e}")
        return []

    with _graph_lock:
        nodes = [n for n in knowledge_graph.nodes() if isinstance(n, str) and len(n) > 2]
        if len(nodes) < 4:
            return []

        # Cache spaCy docs (skip zero-vector concepts)
        node_docs = {}
        for n in nodes:
            doc = nlp(n)
            if doc.vector_norm > 0:
                node_docs[n] = doc

        gaps = {}
        edges = [
            (u, v) for u, v, d in knowledge_graph.edges(data=True)
            if isinstance(u, str) and isinstance(v, str)
            and d.get('weight', 0) > 0.5
            and u in node_docs and v in node_docs
        ]

        for node_a, node_b in edges:
            doc_a = node_docs[node_a]
            doc_b = node_docs[node_b]

            for node_c, doc_c in node_docs.items():
                if node_c in (node_a, node_b):
                    continue
                if (knowledge_graph.has_edge(node_a, node_c) or
                        knowledge_graph.has_edge(node_b, node_c)):
                    continue  # already connected

                try:
                    sim_ac = doc_a.similarity(doc_c)
                    sim_bc = doc_b.similarity(doc_c)
                except Exception:
                    continue

                if sim_ac > 0.55 and sim_bc > 0.55:
                    score = (sim_ac + sim_bc) / 2.0
                    if node_c not in gaps or gaps[node_c]['score'] < score:
                        gaps[node_c] = {
                            'gap_concept':     node_c,
                            'bridge_concepts': [node_a, node_b],
                            'score':           round(score, 4),
                        }

        return sorted(gaps.values(), key=lambda x: -x['score'])[:top_k]


# ─── Graph statistics (for dashboard API) ─────────────────────────────────────

def get_graph_stats() -> dict:
    """Return summary statistics about the knowledge graph."""
    with _graph_lock:
        n_nodes = knowledge_graph.number_of_nodes()
        n_edges = knowledge_graph.number_of_edges()
        string_nodes = [n for n in knowledge_graph.nodes() if isinstance(n, str)]

        avg_memory = 0.0
        if string_nodes:
            scores = [
                knowledge_graph.nodes[n].get('memory_score', 0.5)
                for n in string_nodes
            ]
            avg_memory = sum(scores) / len(scores)

        return {
            'total_nodes':    n_nodes,
            'total_edges':    n_edges,
            'concept_nodes':  len(string_nodes),
            'avg_memory_score': round(avg_memory, 4),
            'density':         round(nx.density(knowledge_graph), 6),
        }


def add_edges(ocr_keywords, audio_label, intent_label, G=None):
    """Add co-occurrence edges between modalities (kept for backward compat)."""
    if G is None:
        G = get_graph()
    try:
        with _graph_lock:
            if ocr_keywords and isinstance(ocr_keywords, dict):
                for kw in ocr_keywords.keys():
                    if kw and str(kw).strip():
                        G.add_edge(("OCR", str(kw)),
                                   ("Intent", str(intent_label)),
                                   type="co_occurrence")
            if audio_label and str(audio_label).strip():
                G.add_edge(("Audio", str(audio_label)),
                           ("Intent", str(intent_label)),
                           type="co_occurrence")
        return G
    except Exception as e:
        logger.warning(f"add_edges error: {e}")
        return G


if __name__ == "__main__":
    sync_db_to_graph()
    stats = get_graph_stats()
    print(f"Graph: {stats['concept_nodes']} concepts, "
          f"{stats['total_edges']} edges, "
          f"avg memory={stats['avg_memory_score']:.3f}")
    gaps = find_knowledge_gaps(top_k=3)
    print(f"Knowledge gaps found: {len(gaps)}")
    for g in gaps:
        print(f"  {g['gap_concept']} (bridges {g['bridge_concepts']}, "
              f"score={g['score']:.3f})")