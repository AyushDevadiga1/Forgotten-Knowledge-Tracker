"""Knowledge-graph endpoints."""

import logging

from flask import Blueprint, jsonify, request

from tracker_app.constants import GRAPH_GAPS_MAX_LIMIT
from tracker_app.web.shared import check_api_key

logger = logging.getLogger("API")

graph_bp = Blueprint("graph", __name__, url_prefix="/api/v1")
graph_bp.before_request(check_api_key)


@graph_bp.route("/graph/stats", methods=["GET"])
def get_graph_stats():
    try:
        from tracker_app.tracking.knowledge_graph import get_graph_stats

        return jsonify({"success": True, "data": get_graph_stats()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@graph_bp.route("/graph/sync", methods=["POST"])
def sync_graph():
    """Force a knowledge-graph resync from the database (F-6).

    Loads the persisted graph if not already in memory, reconciles every
    concept from the DB, and returns the updated graph stats. Intended for
    after a bulk restore or when the graph is suspected to be stale.
    """
    try:
        from tracker_app.tracking.knowledge_graph import sync_db_to_graph

        return jsonify({"success": True, "data": sync_db_to_graph(force=True)})
    except Exception as e:
        logger.error(f"sync_graph: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@graph_bp.route("/graph/gaps", methods=["GET"])
def get_knowledge_gaps():
    try:
        from tracker_app.tracking.knowledge_graph import find_knowledge_gaps

        try:
            limit = int(request.args.get("limit", 5))
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "limit must be an integer"}), 400
        if not (1 <= limit <= GRAPH_GAPS_MAX_LIMIT):
            return jsonify({"success": False, "error": "limit must be 1\u201350"}), 400
        gaps = find_knowledge_gaps(top_k=limit)
        if gaps:
            from tracker_app.db.models import SessionLocal, TrackedConcept

            with SessionLocal() as db:
                rows = db.query(TrackedConcept).filter(TrackedConcept.concept.in_([g["concept"] for g in gaps])).all()
                last_seen = {r.concept: r.last_seen for r in rows}
            for g in gaps:
                ls = last_seen.get(g["concept"])
                g["last_seen"] = ls.isoformat() if ls else None
        return jsonify({"success": True, "data": gaps, "count": len(gaps)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@graph_bp.route("/graph/drift/<concept>", methods=["GET"])
def get_concept_drift(concept):
    try:
        from tracker_app.tracking.knowledge_graph import compute_concept_drift, get_session_concepts

        keywords = get_session_concepts()
        result = compute_concept_drift(concept, keywords)
        result["session_keywords"] = keywords
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@graph_bp.route("/graph/concept/<concept>", methods=["GET"])
def get_concept_detail(concept):
    """Live memory score + encounter history for a concept Ã¢â‚¬â€ backs the
    frontend's click-to-drill-in on a graph node."""
    try:
        from tracker_app.learning.concept_scheduler import ConceptScheduler
        from tracker_app.tracking.knowledge_graph import get_graph

        history = ConceptScheduler().get_concept_history(concept)
        memory = get_graph().nodes.get(concept, {}).get("memory_score", 0.5)
        return jsonify(
            {
                "success": True,
                "data": {
                    "concept": concept,
                    "memory_score": round(float(memory), 4),
                    "history": history,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
