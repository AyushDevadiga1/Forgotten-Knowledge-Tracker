"""Knowledge graph of tracked concepts with JSON persistence and drift/gap analytics."""
import networkx as nx
import numpy as np
import json
import threading
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from tracker_app.config import DATA_DIR, KNOWLEDGE_GRAPH_PATH, DEFAULT_LAMBDA


from tracker_app.utils import utcnow as _utcnow

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
_graph_dirty = False

# Cap on in-memory graph size (H-6): _save_graph() evicts the lowest-
# memory_score zero-edge nodes once the count exceeds this, keeping the
# JSON file small and _load_graph() fast after months of use.
MAX_GRAPH_NODES = 5000

# ----------------------------
# Lazy embedding model
# ----------------------------
# None = never tried; _EMBED_FAILED = load failed (stop retrying + log spam)
_EMBED_FAILED = object()
_embed_model = None

def _get_embed_model():
    """Lazily load SentenceTransformer only when actually needed."""
    global _embed_model
    if _embed_model is _EMBED_FAILED:
        return None
    if _embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embed_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("SentenceTransformer loaded for knowledge graph.")
        except Exception as e:
            logger.warning(f"SentenceTransformer unavailable ({e}). Falling back to spaCy vectors. Will not retry.")
            _embed_model = _EMBED_FAILED
            return None
    return _embed_model

# None = never tried; _SPACY_FAILED = load failed (stop retrying + log spam)
_SPACY_FAILED = object()
_nlp = None

def _get_spacy_vectors(concepts):
    """Fallback: use spaCy word vectors for similarity."""
    global _nlp
    if _nlp is _SPACY_FAILED:
        return None
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.warning(f"spaCy vector fallback unavailable: {e}. Will not retry.")
            _nlp = _SPACY_FAILED
            return None
    try:
        return np.array([_nlp(c).vector for c in concepts])
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
    process restart. The persisted file is a cache: it can always be rebuilt from
    `tracked_concepts`, so a corrupt/missing file is not fatal.
    """
    global _loaded, _last_db_sync
    now = time.monotonic()
    with _graph_lock:
        if not _loaded:
            if knowledge_graph.number_of_nodes() != 0:
                # Graph already populated (e.g. by another module) â€” no file/DB
                # bootstrap needed, but subsequent calls still re-reconcile.
                _loaded = True
            else:
                if not _load_graph_locked():
                    logger.info("No persisted knowledge graph; building from DB.")
                else:
                    logger.info("Knowledge graph loaded from %s", KNOWLEDGE_GRAPH_PATH)
                sync_db_to_graph()  # reconcile (or first-build) then persist
                _loaded = True
            _last_db_sync = now
        elif now - _last_db_sync >= DB_SYNC_INTERVAL_SECONDS:
            sync_db_to_graph()
            _last_db_sync = now

def _jsonable(obj):
    """Convert numpy scalars/arrays (and containers of them) to plain JSON types."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def _load_graph_locked() -> bool:
    """Load a persisted graph from KNOWLEDGE_GRAPH_PATH. Returns True on success.

    Tries the JSON format first; on failure falls back to legacy pickle files
    (the configured path itself, then a sibling knowledge_graph.pkl from before
    the JSON migration), migrating any pickle found to JSON on success. The
    graph is a rebuildable cache: a corrupt/missing file is not fatal.

    Must be called with `_graph_lock` already held (M-9): this function
    mutates the shared in-memory graph and never acquires the lock itself --
    the caller's acquire is the single point of entry.
    """
    global _graph_dirty
    path = Path(KNOWLEDGE_GRAPH_PATH)

    def _apply_json(data) -> bool:
        if not (isinstance(data, dict)
                and isinstance(data.get('nodes'), list)
                and isinstance(data.get('edges'), list)):
            return False
        knowledge_graph.clear()
        knowledge_graph.add_nodes_from(
            (n, dict(attrs)) for n, attrs in data['nodes']
        )
        knowledge_graph.add_edges_from(
            (u, v, dict(attrs)) for u, v, attrs in data['edges']
        )
        return knowledge_graph.number_of_nodes() > 0

    # 1. Current JSON format.
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if _apply_json(data):
                _graph_dirty = False
                return True
        except Exception as e:
            logger.warning("Failed to load knowledge graph JSON from %s: %s", path, e)

    # 2. Legacy pickle auto-migration: the configured path itself, then the
    # pre-migration default name next to it (DATA_DIR/knowledge_graph.pkl).
    import pickle  # legacy read-only fallback; JSON is the write format now
    candidates = [path]
    legacy = path.parent / "knowledge_graph.pkl"
    if legacy != path:
        candidates.append(legacy)
    for cand in candidates:
        if not cand.exists():
            continue
        try:
            with open(cand, 'rb') as f:
                data = pickle.load(f)
            if not isinstance(data, nx.Graph) or data.number_of_nodes() == 0:
                continue
            knowledge_graph.clear()
            knowledge_graph.add_nodes_from(data.nodes(data=True))
            knowledge_graph.add_edges_from(data.edges(data=True))
            logger.info("Migrating legacy pickle knowledge graph %s -> %s", cand, path)
            _save_graph()
            _graph_dirty = False
            return True
        except Exception as e:
            logger.warning("Failed to load legacy knowledge graph from %s: %s", cand, e)
    return False

def _evict_oversized_nodes():
    """Trim the graph back to MAX_GRAPH_NODES (best-effort, H-6).

    Only nodes with zero edges and the lowest memory_score are evicted, so
    no semantic structure is destroyed. The graph is a rebuildable cache of
    tracked_concepts; an evicted node is simply re-added by the next DB sync.
    """
    excess = knowledge_graph.number_of_nodes() - MAX_GRAPH_NODES
    if excess <= 0:
        return
    with _graph_lock:
        excess = knowledge_graph.number_of_nodes() - MAX_GRAPH_NODES
        if excess <= 0:
            return
        candidates = [
            n for n in knowledge_graph.nodes()
            if knowledge_graph.degree(n) == 0
        ]
        candidates.sort(
            key=lambda n: knowledge_graph.nodes[n].get('memory_score', 0.5)
        )
        evicted = 0
        for node in candidates:
            if evicted >= excess:
                break
            knowledge_graph.remove_node(node)
            evicted += 1
        if evicted:
            logger.info(
                "Evicted %d low-relevance zero-edge nodes (graph cap %d)",
                evicted, MAX_GRAPH_NODES,
            )


def _save_graph():
    """Persist the in-memory graph to KNOWLEDGE_GRAPH_PATH as JSON (atomic write)."""
    global _graph_dirty
    try:
        _evict_oversized_nodes()
        path = Path(KNOWLEDGE_GRAPH_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'nodes': [
                [n, _jsonable(dict(d))]
                for n, d in knowledge_graph.nodes(data=True)
            ],
            'edges': [
                [u, v, _jsonable(dict(d))]
                for u, v, d in knowledge_graph.edges(data=True)
            ],
        }
        tmp = path.with_name(path.name + '.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(payload, f)
        tmp.replace(path)
        _graph_dirty = False
        logger.debug("Knowledge graph saved to %s", path)
    except Exception as e:
        logger.warning("Failed to save knowledge graph: %s", e)

def fetch_concepts_from_db():
    """Fetch concepts from tracked_concepts table (NOT window titles)."""
    try:
        from tracker_app.db.models import SessionLocal, TrackedConcept
        with SessionLocal() as db:
            rows = (
                db.query(TrackedConcept.concept)
                  .filter(TrackedConcept.concept.isnot(None))
                  .distinct()
                  .all()
            )
            concepts = [r.concept.strip() for (r,) in rows if r and r.strip()]
            return concepts
    except Exception as e:
        logger.error(f"Error fetching concepts from DB: {e}")
        return []
def _memory_score_from_row(row):
    """Live AWFC retention for a TrackedConcept row (0.05â€“1.0).

    Uses the concept's personalised lambda and attention-at-encoding, with the
    decay clock reset at the last encounter/review.
    """
    from tracker_app.learning.memory_model import compute_memory_score_awfc
    last_review = row.last_seen or row.first_seen or _utcnow()
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
    global _graph_dirty
    if not concepts:
        return

    valid_concepts = [str(c).strip() for c in concepts if c and str(c).strip()]
    if not valid_concepts:
        return

    # Try to get embeddings â€” optional, graceful fallback
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
                emb = embeddings[idx] if embeddings is not None else []
                knowledge_graph.add_node(
                    concept,
                    embedding=emb.tolist() if hasattr(emb, "tolist") else list(emb),
                    count=1,
                    memory_score=live_scores.get(concept, 0.3),
                    next_review_time=_utcnow().strftime(DATETIME_FORMAT),
                    last_review=_utcnow().strftime(DATETIME_FORMAT),
                    intent_conf=1.0
                )
                _graph_dirty = True
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
    contact too â€” the micro-quiz's 'weakest concept' selection and graph stats
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
    global _graph_dirty
    if concept not in knowledge_graph:
        return False
    with _graph_lock:
        if concept in knowledge_graph:
            knowledge_graph.remove_node(concept)
            _graph_dirty = True
    if _graph_dirty:
        _save_graph()
    return True


def _refresh_all_memory_scores(concepts):
    """Batch-refresh graph node memory fields from live DB state (Phase 11.2).

    The graph is a cache; without this its memory_score stays frozen at the
    value assigned at node creation, so the dashboard's average memory and the
    micro-quiz's 'weakest concept' selection never reflect real progress.
    """
    global _graph_dirty
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
            new_score = round(score, 4)
            if node.get('memory_score') != new_score:
                _graph_dirty = True
            node['memory_score']    = new_score
            node['interval']        = interval
            node['memory_strength'] = strength
            if isinstance(last_seen, datetime):
                node['last_review'] = last_seen.strftime(DATETIME_FORMAT)


def sync_db_to_graph(force: bool = False) -> dict:
    """Synchronize database concepts to graph.

    Incremental: only concepts missing from the in-memory graph get new nodes
    (and embeddings), so a load-from-pkl + reconcile does not re-embed every
    concept. Existing nodes get their memory fields refreshed from live DB
    state. Persists the graph afterwards.

    With force=True the in-memory graph is loaded from the pkl first if it is
    not already loaded, then the reconcile runs immediately without waiting on
    the DB_SYNC_INTERVAL_SECONDS throttle -- the behaviour behind the
    /graph/sync endpoint (F-6). add_concepts() dedupes on the node key, so a
    force re-run never duplicates nodes or inflates the returned counts.

    Returns {'nodes', 'edges', 'synced'} so callers (the F-6 endpoint) can
    answer with the updated graph stats. Existing callers that ignored the
    previous None return are unaffected.
    """
    try:
        if force:
            _ensure_graph_loaded()
        db_concepts = fetch_concepts_from_db()
        new_concepts = [c for c in db_concepts if c not in knowledge_graph]
        if new_concepts:
            add_concepts(new_concepts)
        _refresh_all_memory_scores(db_concepts)
        if _graph_dirty:
            _save_graph()
        logger.info("Synced %d concepts from DB to graph (%d new%s)",
                    len(db_concepts), len(new_concepts),
                    ", forced" if force else "")
        return {
            "nodes": knowledge_graph.number_of_nodes(),
            "edges": knowledge_graph.number_of_edges(),
            "synced": len(new_concepts),
        }
    except Exception as e:
        logger.warning("Error syncing DB to graph: %s", e)
        return {"nodes": 0, "edges": 0, "synced": 0}

def get_graph():
    """Get graph with thread-safe access"""
    _ensure_graph_loaded()
    return knowledge_graph


# â”€â”€â”€ Concept Drift Detector â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
            start = _utcnow() - timedelta(minutes=15)

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


# â”€â”€â”€ Knowledge Gap Map â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


# â”€â”€â”€ Graph statistics (for dashboard API) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
            avg_memory = float(sum(scores)) / len(scores)

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
                [u, v, round(float(data.get('weight', 1.0)), 4)]
                for u, v, data in knowledge_graph.edges(data=True)
                if u in top_set and v in top_set
            ),
            key=lambda e: e[2],
            reverse=True,
        )

        # Per-node live memory scores for the visible top set â€” the frontend
        # force-layout sizes/colours nodes from these (weak = small/dim).
        nodes = [
            {
                'concept': n,
                'memory_score': float(knowledge_graph.nodes[n].get('memory_score', 0.5)),
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
