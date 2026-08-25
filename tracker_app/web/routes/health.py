"""Health probe endpoint.

Lives in its own blueprint and deliberately carries NO auth hooks: the
health check must stay reachable without an API key (this was previously
enforced by an endpoint-name exemption inside the shared auth hooks).
"""

from flask import Blueprint, jsonify

from tracker_app.utils import utcnow as _utcnow

health_bp = Blueprint("health", __name__, url_prefix="/api/v1")


@health_bp.route("/health", methods=["GET"])
def health_check():
    try:
        from tracker_app.db.models import SessionLocal
        from tracker_app.db.repository import LearningRepository, FeedbackRepository

        with SessionLocal() as db:
            item_count = LearningRepository.get_total_count(db)
            feedback_count = FeedbackRepository.get_total_count(db)
        return jsonify(
            {
                "status": "healthy",
                "timestamp": _utcnow().isoformat(),
                "version": "2.0.0",  # keep in sync with tracker_app.__version__
                "components": {
                    "database": "reachable",
                    "item_count": item_count,
                    "feedback_count": feedback_count,
                    "api": "online",
                },
            }
        ), 200
    except Exception as e:
        return jsonify(
            {
                "status": "unhealthy",
                "error": str(e),
            }
        ), 503
