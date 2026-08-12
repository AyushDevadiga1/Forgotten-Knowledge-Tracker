"""Knowledge graph of tracked concepts with pkl persistence and drift/gap analytics."""
import networkx as nx
import numpy as np
import pickle
import sqlite3
import threading
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from tracker_app.config import DB_PATH, KNOWLEDGE_GRAPH_PATH, DEFAULT_LAMBDA

logger = logging.getLogger("KnowledgeGraph")

# Consistent datetime format across all modules
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Thread safety lock for graph operations
_graph_lock = threading.RLock()

# How often a loaded graph re-reconciles against the DB (so concepts captured
# mid-process become visible to quiz selection / stats without a restart).
DB_SYNC_INTERVAL_SECONDS = 60.0
_loaded = False
_last_db_sync = 0.0

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


def _ensure_graph_loaded():
    """Populate the in-memory graph on first use, then re-reconcile periodically.

    Loads the persisted graph (nodes, embeddings, edges) from
    KNOWLEDGE_GRAPH_PATH when available, then reconciles any concepts the DB
    gained since the last save. Falls back to a full DB sync when no persisted
    graph exists. After the initial load, a throttled DB re-sync runs at most
    once per DB_SYNC_INTERVAL_SECONDS so concepts captured mid-process (tracker
    loop, browser ingest) surface in quiz selection and graph stats without a
    process restart. The pkl is a cache: it can always be rebuilt from
    `tracked_concepts`, so a corrupt/missing file is not fatal.
    """
    global _loaded, _last_db_sync
    now = time.monotonic()
    with _graph_lock:
        if not _loaded:
            if knowledge_graph.number_of_nodes() != 0:
                # Graph already populated (e.g. by another module) — no pkl/DB
                # bootstrap needed, but subsequent calls still re-reconcile.
                _loaded = True
            else:
                if not _load_graph():
                    logger.info("No persisted knowledge graph; building from DB.")
                else:
                    logger.info("Knowledge graph loaded from %s", KNOWLEDGE_GRAPH_PATH)
                sync_db_to_graph()  # reconcile (or first-build) then persist
                _loaded = True
            _last_db_sync = now
        elif now - _last_db_sync >= DB_SYNC_INTERVAL_SECONDS:
            sync_db_to_graph()
            _last_db_sync = now

def _load_graph() -> bool:
    """Load a persisted graph from KNOWLEDGE_GRAPH_PATH. Returns True on success."""
    path = Path(KNOWLEDGE_GRAPH_PATH)
    if not path.exists():
        return False
    try:
        with open(path, 'rb') as f:
            data = pickle.load(f)
        if not isinstance(data, nx.Graph) or data.number_of_nodes() == 0:
            return False
        with _graph_lock:
            knowledge_graph.clear()
            knowledge_graph.add_nodes_from(data.nodes(data=True))
            knowledge_graph.add_edges_from(data.edges(data=True))
        return True
    except Exception as e:
        logger.warning("Failed to load knowledge graph from %s: %s", path, e)
        return False

def _save_graph():
    """Persist the in-memory graph to KNOWLEDGE_GRAPH_PATH (best-effort cache)."""
    try:
        path = Path(KNOWLEDGE_GRAPH_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.pkl.tmp')
        with open(tmp, 'wb') as f:
            pickle.dump(knowledge_graph, f, protocol=pickle.HIGHEST_PROTOCOL)
        tmp.replace(path)
        logger.debug("Knowledge graph saved to %s", path)
    except Exception as e:
        logger.warning("Failed to save knowledge graph: %s", e)

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

def _memory_score_from_row(row):
    """Live AWFC retention for a TrackedConcept row (0.05–1.0).

    Uses the concept's personalised lambda and attention-at-encoding, with the
    decay clock reset at the last encounter/review.
    """
    from tracker_app.learning.memory_model import compute_memory_score_awfc
    last_review = row.last_seen or row.first_seen or datetime.utcnow()
    return compute_memory_score_awfc(
        last_review,
        base_lambda=row.lambda_personalised or DEFAULT_LAMBDA,
        attention_at_encoding=row.attention_at_encoding or 50.0,
    )


def _fetch_live_memory_scores(concepts):
    """Return {concept: live AWFC memory_score} for concepts present in the DB."""
    if not concepts:
        return {}
    try:
        from tracker_app.db.models import SessionLocal, TrackedConcept
        with SessionLocal() as db:
            rows = db.query(TrackedConcept).filter(
                TrackedConcept.concept.in_(concepts)).all()
        return {r.concept: _memory_score_from_row(r) for r in rows}
    except Exception as e:
        logger.debug(f"_fetch_live_memory_scores failed: {e}")
        return {}


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
        # Pull live memory state so new nodes don't start frozen at 0.3 (Phase 11.2).
        live_scores = _fetch_live_memory_scores(valid_concepts)
        for idx, concept in enumerate(valid_concepts):
            if concept not in knowledge_graph:
                knowledge_graph.add_node(
                    concept,
                    embedding=embeddings[idx].tolist() if embeddings is not None else [],
                    count=1,
                    memory_score=live_scores.get(concept, 0.3),
                    next_review_time=datetime.utcnow().strftime(DATETIME_FORMAT),
                    last_review=datetime.utcnow().strftime(DATETIME_FORMAT),
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

def sync_concept_to_graph(concept):
    """Refresh one graph node's memory fields from the live DB row.

    Called when a concept is re-encountered or reviewed so the in-memory graph
    stays in step with SM-2/AWFC state. A concept the DB gained after the graph
    was last built (mid-session capture, browser ingest) is added on first
    contact too — the micro-quiz's 'weakest concept' selection and graph stats
    must never serve a graph frozen at first load.
    """
    if concept not in knowledge_graph:
        # Node missing: add it from the live DB row (pull live AWFC score).
        try:
            from tracker_app.db.models import SessionLocal, TrackedConcept
            with SessionLocal() as db:
                exists = db.query(TrackedConcept.concept).filter(
                    TrackedConcept.concept == concept).first() is not None
        except Exception as e:
            logger.debug(f"sync_concept_to_graph lookup failed for {concept}: {e}")
            return
        if exists:
            add_concepts([concept])
        if concept not in knowledge_graph:
            return
    try:
        from tracker_app.db.models import SessionLocal, TrackedConcept
        with SessionLocal() as db:
            row = db.query(TrackedConcept).filter(
                TrackedConcept.concept == concept).first()
            if row is None:
                return
            score      = _memory_score_from_row(row)
            interval   = getattr(row, "interval", 1) or 1
            strength   = getattr(row, "memory_strength", 2.5) or 2.5
            last_seen  = row.last_seen or row.first_seen
        with _graph_lock:
            node = knowledge_graph.nodes[concept]
            node['memory_score']    = round(score, 4)
            node['interval']        = interval
            node['memory_strength'] = strength
            if isinstance(last_seen, datetime):
                node['last_review'] = last_seen.strftime(DATETIME_FORMAT)
    except Exception as e:
        logger.debug(f"sync_concept_to_graph failed for {concept}: {e}")


def remove_concept_from_graph(concept):
    """Remove a concept node (and its edges) from the in-memory graph.

    Called when a tracked concept is permanently deleted so the dashboard and
    micro-quiz never surface knowledge we agreed to forget. Best-effort and
    idempotent; the graph is a rebuildable cache from tracked_concepts.
    """
    if concept not in knowledge_graph:
        return False
    with _graph_lock:
        if concept in knowledge_graph:
            knowledge_graph.remove_node(concept)
    _save_graph()
    return True


def _refresh_all_memory_scores(concepts):
    """Batch-refresh graph node memory fields from live DB state (Phase 11.2).

    The graph is a cache; without this its memory_score stays frozen at the
    value assigned at node creation, so the dashboard's average memory and the
    micro-quiz's 'weakest concept' selection never reflect real progress.
    """
    if not concepts:
        return
    try:
        from tracker_app.db.models import SessionLocal, TrackedConcept
        with SessionLocal() as db:
            rows = db.query(TrackedConcept).filter(
                TrackedConcept.concept.in_(concepts)).all()
    except Exception as e:
        logger.debug(f"_refresh_all_memory_scores failed: {e}")
        return
    updates = {}
    for r in rows:
        if r.concept in knowledge_graph:
            updates[r.concept] = (
                _memory_score_from_row(r),
                getattr(r, "interval", 1) or 1,
                getattr(r, "memory_strength", 2.5) or 2.5,
                r.last_seen or r.first_seen,
            )
    with _graph_lock:
        for concept, (score, interval, strength, last_seen) in updates.items():
            node = knowledge_graph.nodes[concept]
            node['memory_score']    = round(score, 4)
            node['interval']        = interval
            node['memory_strength'] = strength
            if isinstance(last_seen, datetime):
                node['last_review'] = last_seen.strftime(DATETIME_FORMAT)


def sync_db_to_graph():
    """Synchronize database concepts to graph.

    Incremental: only concepts missing from the in-memory graph get new nodes
    (and embeddings), so a load-from-pkl + reconcile does not re-embed every
    concept. Existing nodes get their memory fields refreshed from live DB
    state. Persists the graph afterwards.
    """
    try:
        db_concepts = fetch_concepts_from_db()
        new_concepts = [c for c in db_concepts if c not in knowledge_graph]
        if new_concepts:
            add_concepts(new_concepts)
        _refresh_all_memory_scores(db_concepts)
        _save_graph()
        logger.info("Synced %d concepts from DB to graph (%d new)",
                    len(db_concepts), len(new_concepts))
    except Exception as e:
        logger.warning("Error syncing DB to graph: %s", e)

def get_graph():
    """Get graph with thread-safe access"""
    _ensure_graph_loaded()
    return knowledge_graph


# ─── Concept Drift Detector ───────────────────────────────────────────────────

def get_session_concepts(limit: int = 50) -> list:
    """Concepts encountered during the active study session.

    Falls back to the last 15 minutes when no session is active. Drift needs
    the concepts that actually co-occurred with the target concept while
    studying; an empty keyword list made every drift call report 'new' with
    drift_score 0.0. Timestamps are naive UTC, matching ConceptEncounter.
    """
    try:
        from tracker_app.db.models import SessionLocal, ConceptEncounter
        from tracker_app.tracking.session_state import get_status

        start = None
        status = get_status()
        if status.get("active") and status.get("started_at"):
            try:
                start = datetime.fromisoformat(status["started_at"])
            except (ValueError, TypeError):
                start = None
        if start is None:
            start = datetime.utcnow() - timedelta(minutes=15)

        with SessionLocal() as db:
            rows = (
                db.query(ConceptEncounter.concept)
                .filter(ConceptEncounter.timestamp >= start)
                .order_by(ConceptEncounter.timestamp.desc())
                .limit(limit)
                .all()
            )
        return [r[0] for r in rows if r[0] and str(r[0]).strip()]
    except Exception as e:
        logger.debug(f"get_session_concepts failed: {e}")
        return []


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
    _ensure_graph_loaded()
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
        else:
            status = 'stable'

        return {
            'concept':              concept,
            'drift_score':          round(drift, 4),
            'status':               status,
            'co_concepts_now':      sorted(current_neighbours),
            'co_concepts_historic': sorted(historic_neighbours),
        }


# ─── Knowledge Gap Map ────────────────────────────────────────────────────────

def find_knowledge_gaps(top_k: int = 5) -> list:
    """
    Identify concepts the user probably should know but hasn't encountered.

    Algorithm:
      For every pair (A, B) with a strong edge (weight > 0.5),
      find concepts C in the graph that:
        - are cosine-similar to both A and B (similarity > 0.55) using the
          SAME node embeddings that built the edges (stored on each node)
        - are NOT directly connected to either A or B
      Surface C as a 'knowledge gap' with a score = avg(sim(A,C), sim(B,C)).

    Returns:
        List of dicts sorted by score descending:
        [{'gap_concept': str, 'bridge_concepts': [str, str], 'score': float}]
    """
    _ensure_graph_loaded()

    with _graph_lock:
        nodes = [n for n in knowledge_graph.nodes() if isinstance(n, str) and len(n) > 2]
        if len(nodes) < 4:
            return []

        # Reuse the embeddings stored on nodes at add_concepts() time so gap
        # detection uses the identical representation as edge building
        # (SentenceTransformer with spaCy fallback) instead of loading spaCy
        # again independently.
        node_vecs = {}
        for n in nodes:
            emb = knowledge_graph.nodes[n].get('embedding')
            if not emb:
                continue
            arr = np.asarray(emb, dtype=float)
            norm = np.linalg.norm(arr)
            if norm > 0:
                node_vecs[n] = arr / norm

        gaps = {}
        edges = [
            (u, v) for u, v, d in knowledge_graph.edges(data=True)
            if isinstance(u, str) and isinstance(v, str)
            and d.get('weight', 0) > 0.5
            and u in node_vecs and v in node_vecs
        ]

        for node_a, node_b in edges:
            vec_a = node_vecs[node_a]
            vec_b = node_vecs[node_b]

            for node_c, vec_c in node_vecs.items():
                if node_c in (node_a, node_b):
                    continue
                if (knowledge_graph.has_edge(node_a, node_c) or
                        knowledge_graph.has_edge(node_b, node_c)):
                    continue  # already connected

                sim_ac = float(np.dot(vec_a, vec_c))
                sim_bc = float(np.dot(vec_b, vec_c))

                if sim_ac > 0.55 and sim_bc > 0.55:
                    score = (sim_ac + sim_bc) / 2.0
                    if node_c not in gaps or gaps[node_c]['score'] < score:
                        gaps[node_c] = {
                            'gap_concept':     node_c,
                            'concept':         node_c,
                            'bridge_concepts': [node_a, node_b],
                            'score':           round(score, 4),
                            'memory_strength': round(score, 4),
                            'gap_score':       round(score, 4),
                        }

        return sorted(gaps.values(), key=lambda x: -x['score'])[:top_k]


# ─── Graph statistics (for dashboard API) ─────────────────────────────────────

def get_graph_stats() -> dict:
    """Return summary statistics about the knowledge graph."""
    _ensure_graph_loaded()
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

        top_concepts = sorted(
            (n for n in string_nodes),
            key=lambda n: knowledge_graph.nodes[n].get('memory_score', 0.5),
            reverse=True,
        )[:10]

        # Real edges among the visible top concepts (M-7). The frontend used to
        # fabricate spoke lines from a fake "HUB"; return the actual weighted
        # semantic edges so the map draws the true graph structure.
        top_set = set(top_concepts)
        edges = sorted(
            (
                [u, v, round(data.get('weight', 1.0), 4)]
                for u, v, data in knowledge_graph.edges(data=True)
                if u in top_set and v in top_set
            ),
            key=lambda e: e[2],
            reverse=True,
        )

        # Per-node live memory scores for the visible top set — the frontend
        # force-layout sizes/colours nodes from these (weak = small/dim).
        nodes = [
            {
                'concept': n,
                'memory_score': knowledge_graph.nodes[n].get('memory_score', 0.5),
            }
            for n in top_concepts
        ]

        return {
            'total_nodes':    n_nodes,
            'total_edges':    n_edges,
            'concept_nodes':  len(string_nodes),
            'avg_memory_score': round(avg_memory, 4),
            'density':         round(nx.density(knowledge_graph), 6),
            # dashboard (frontend) keys
            'total_concepts':  len(string_nodes),
            'avg_memory_strength': round(avg_memory, 4),
            'top_concepts':    top_concepts,
            'nodes':           nodes,
            'edges':           edges,  # [source, target, weight]
        }


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