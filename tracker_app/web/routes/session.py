"""Study-session endpoints (Phase 9 - session-gated concept capture), review
recording, and the right-to-be-forgotten concept deletion."""

import logging

from flask import Blueprint, jsonify, request

from tracker_app.constants import SM2_MIN_QUALITY, SM2_MAX_QUALITY
from tracker_app.web.shared import check_api_key, get_tracker

logger = logging.getLogger("API")

session_bp = Blueprint("session", __name__, url_prefix="/api/v1")
session_bp.before_request(check_api_key)


@session_bp.route("/reviews", methods=["POST"])
def record_review():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Request body must be valid JSON"}), 400
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400

    item_id = data.get("item_id", "")
    if item_id is None:
        return jsonify({"success": False, "error": "item_id is required"}), 400
    if not isinstance(item_id, str):
        item_id = str(item_id)  # JSON numbers are valid ids - never crash on .strip()
    item_id = item_id.strip()
    if not item_id:
        return jsonify({"success": False, "error": "item_id is required"}), 400

    try:
        quality = int(data.get("quality", 3))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "quality must be an integer"}), 400

    if not (SM2_MIN_QUALITY <= quality <= SM2_MAX_QUALITY):
        return jsonify({"success": False, "error": "quality must be 0Ã¢â‚¬â€œ5"}), 400

    try:
        get_tracker().record_review(item_id=item_id, quality_rating=quality)
        return jsonify({"success": True, "message": "Review recorded"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@session_bp.route("/concepts/<concept>", methods=["DELETE"])
def delete_concept(concept):
    """Permanently remove a tracked concept, its encounter history, and its
    knowledge-graph node. This is the right-to-be-forgotten path for anything
    passively captured (e.g. a stray sensitive term)."""
    try:
        from tracker_app.db.models import SessionLocal, TrackedConcept
        from tracker_app.tracking.knowledge_graph import remove_concept_from_graph

        with SessionLocal() as db:
            row = db.query(TrackedConcept).filter(TrackedConcept.concept == concept).first()
            if not row:
                return jsonify({"success": False, "error": "Concept not found"}), 404
            db.delete(row)  # ConceptEncounter rows cascade via ORM
            db.commit()
        remove_concept_from_graph(concept)
        return jsonify({"success": True, "message": "Concept deleted"})
    except Exception as e:
        logger.error(f"delete_concept: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@session_bp.route("/session/status", methods=["GET"])
def get_session_status():
    """Return whether a study session is currently active and when it started."""
    try:
        from tracker_app.tracking.session_state import get_status

        return jsonify({"success": True, "data": get_status()})
    except Exception as e:
        logger.error(f"get_session_status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@session_bp.route("/session/start", methods=["POST"])
def start_study_session():
    """Toggle a study session on Ã¢â‚¬â€ the tracker loop only captures concepts
    while a session is active."""
    try:
        from tracker_app.tracking.session_state import start

        return jsonify({"success": True, "data": start()})
    except Exception as e:
        logger.error(f"start_study_session: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@session_bp.route("/session/stop", methods=["POST"])
def stop_study_session():
    """Toggle a study session off Ã¢â‚¬â€ capture pauses and analytics are saved."""
    try:
        from tracker_app.tracking.session_state import stop

        return jsonify({"success": True, "data": stop()})
    except Exception as e:
        logger.error(f"stop_study_session: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# --- EAR Calibration ---


@session_bp.route("/session/calibrate", methods=["POST"])
def calibrate_session():
    """Trigger EAR calibration for the current session."""
    try:
        from tracker_app.config import CALIBRATION_DURATION_SECONDS
        from tracker_app.tracking.webcam_module import calibrate_ear
        from tracker_app.tracking.session_state import set_calibration

        duration = CALIBRATION_DURATION_SECONDS
        try:
            req = request.get_json(silent=True) or {}
            if "duration_seconds" in req:
                duration = int(req["duration_seconds"])
        except Exception as exc:
            logger.debug("parsing duration failed: %s", exc)
        result = calibrate_ear(duration)
        set_calibration(result)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error("calibrate_session: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
