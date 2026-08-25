"""Learning-item endpoints: CRUD, search, archive, due queue, backfill, export."""

import json
import logging

from flask import Blueprint, jsonify, request

from tracker_app.constants import QUESTION_MAX_LENGTH
from tracker_app.learning.learning_tracker import DifficultyLevel, LearningItemType
from tracker_app.web.shared import check_api_key, get_tracker

logger = logging.getLogger("API")

items_bp = Blueprint("items", __name__, url_prefix="/api/v1")
items_bp.before_request(check_api_key)

VALID_STATUSES = {"active", "mastered", "archived", "all"}
MAX_LIMIT = 500


# ---------------------------------------------------------------------------
# Learning Items
# ---------------------------------------------------------------------------


@items_bp.route("/items", methods=["GET"])
def get_items():
    try:
        limit = int(request.args.get("limit", 50))
        if not (1 <= limit <= MAX_LIMIT):
            return jsonify({"success": False, "error": f"limit must be 1Ã¢â‚¬â€œ{MAX_LIMIT}"}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "limit must be an integer"}), 400

    status = request.args.get("status", "active")
    if status not in VALID_STATUSES:
        return jsonify({"success": False, "error": f"status must be one of: {sorted(VALID_STATUSES)}"}), 400
    try:
        items = get_tracker().get_items(status=status, limit=limit)
        return jsonify({"success": True, "data": items, "count": len(items)})
    except Exception as e:
        logger.error(f"get_items: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@items_bp.route("/items", methods=["POST"])
def create_item():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Request body must be valid JSON"}), 400
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400

    question = data.get("question", "") or ""
    answer = data.get("answer", "") or ""
    if not isinstance(question, str):
        question = str(question)  # JSON numbers must not crash .strip()
    if not isinstance(answer, str):
        answer = str(answer)
    question = question.strip()
    answer = answer.strip()

    if not question:
        return jsonify({"success": False, "error": "question is required"}), 400
    if not answer:
        return jsonify({"success": False, "error": "answer is required"}), 400
    if len(question) > QUESTION_MAX_LENGTH:
        return jsonify({"success": False, "error": "question must be under 1000 chars"}), 400

    difficulty = data.get("difficulty", "medium")
    if difficulty not in {"easy", "medium", "hard"}:
        return jsonify({"success": False, "error": "difficulty must be easy/medium/hard"}), 400

    item_type = data.get("item_type", "concept")
    valid_item_types = {t.value for t in LearningItemType}
    if item_type not in valid_item_types:
        return jsonify(
            {"success": False, "error": "item_type must be one of: " + ", ".join(sorted(valid_item_types))}
        ), 400

    try:
        item_id = get_tracker().add_learning_item(
            question=question,
            answer=answer,
            difficulty=DifficultyLevel(difficulty).value,
            item_type=LearningItemType(item_type).value,
            tags=data.get("tags", []),
        )
        return jsonify({"success": True, "data": {"id": item_id}}), 201
    except Exception as e:
        logger.error(f"create_item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@items_bp.route("/items/backfill", methods=["POST"])
def backfill_items():
    """One-shot migration: promote validated extracted concepts from
    tracked_concepts into the SM-2 learning deck. Idempotent Ã¢â‚¬â€ concepts with
    an existing deck item (exact question match) are skipped."""
    try:
        from tracker_app.learning.concept_promotion import backfill_items as run_backfill

        min_frequency = request.args.get("min_frequency", 3)
        try:
            min_frequency = int(min_frequency)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "min_frequency must be an integer"}), 400
        if not (1 <= min_frequency <= 1000):
            return jsonify({"success": False, "error": "min_frequency must be 1Ã¢â‚¬â€œ1000"}), 400
        result = run_backfill(min_frequency=min_frequency)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"backfill_items: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@items_bp.route("/items/due", methods=["GET"])
def get_due_items():
    try:
        items = get_tracker().get_items_due()
        return jsonify({"success": True, "data": items, "count": len(items)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@items_bp.route("/items/<item_id>", methods=["GET"])
def get_item(item_id):
    try:
        item = get_tracker().get_item(item_id)
        if not item:
            return jsonify({"success": False, "error": "Item not found"}), 404
        return jsonify({"success": True, "data": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@items_bp.route("/items/<item_id>", methods=["DELETE"])
def delete_item(item_id):
    """Permanently remove a learning item and its review history."""
    try:
        deleted = get_tracker().delete_item(item_id)
        if not deleted:
            return jsonify({"success": False, "error": "Item not found"}), 404
        return jsonify({"success": True, "message": "Item deleted"})
    except Exception as e:
        logger.error(f"delete_item: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@items_bp.route("/items/<item_id>/archive", methods=["POST"])
def archive_item(item_id):
    """Archive a learning item."""
    try:
        get_tracker().archive_item(item_id)
        return jsonify({"success": True, "message": f"Item {item_id} archived"})
    except Exception as e:
        logger.error("archive_item: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@items_bp.route("/items/<item_id>/unarchive", methods=["POST"])
def unarchive_item(item_id):
    """Unarchive a learning item."""
    try:
        get_tracker().unarchive_item(item_id)
        return jsonify({"success": True, "message": f"Item {item_id} unarchived"})
    except Exception as e:
        logger.error("unarchive_item: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# --- M4: Orphaned feature endpoints ---

@items_bp.route("/search", methods=["GET"])
def search_items():
    """Search learning items by query string."""
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"success": False, "error": "Missing query parameter 'q'"}), 400
        results = get_tracker().search_items(query)
        return jsonify({"success": True, "data": results, "count": len(results)})
    except Exception as e:
        logger.error("search_items: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@items_bp.route("/export", methods=["GET"])
def export_items():
    """Export learning items as JSON or Anki-importable TSV."""
    try:
        fmt = request.args.get("format", "json")
        if fmt not in ("json", "anki"):
            return jsonify({"success": False, "error": "format must be 'json' or 'anki'"}), 400
        exported = get_tracker().export_items(format=fmt)
        if fmt == "anki":
            return exported, 200, {"Content-Type": "text/tab-separated-values; charset=utf-8",
                                    "Content-Disposition": "attachment; filename=fkt_export.tsv"}
        return jsonify({"success": True, "data": json.loads(exported)})
    except Exception as e:
        logger.error("export_items: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
