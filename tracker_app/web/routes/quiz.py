"""Micro-quiz endpoints."""

import logging

from flask import Blueprint, jsonify, request

from tracker_app.web.shared import _parse_bool_flag, check_api_key

logger = logging.getLogger("API")

quiz_bp = Blueprint("quiz", __name__, url_prefix="/api/v1")
quiz_bp.before_request(check_api_key)


@quiz_bp.route("/quiz/current", methods=["GET"])
def get_current_quiz():
    try:
        from tracker_app.tracking.quiz_engine import generate_quiz
        from tracker_app.tracking.knowledge_graph import get_graph

        quiz_type = request.args.get("type")
        quiz = generate_quiz(get_graph(), quiz_type=quiz_type)
        return jsonify({"success": True, "data": quiz})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@quiz_bp.route("/quiz/answer", methods=["POST"])
def submit_quiz_answer():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Request body must be valid JSON"}), 400
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400
    if "concept" not in data or "was_correct" not in data:
        return jsonify({"success": False, "error": "concept and was_correct are required"}), 400
    was_correct = _parse_bool_flag(data["was_correct"])
    if was_correct is None:
        return jsonify({"success": False, "error": "was_correct must be a boolean"}), 400
    try:
        from tracker_app.tracking.quiz_engine import record_quiz_result

        record_quiz_result(str(data["concept"]), was_correct)
        return jsonify({"success": True, "message": "Quiz result recorded in SM-2"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
