"""Stats and tracking-history endpoints."""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from tracker_app.constants import GRAPH_GAPS_MAX_DAYS
from tracker_app.web.shared import check_api_key, get_tracker

logger = logging.getLogger("API")

stats_bp = Blueprint("stats", __name__, url_prefix="/api/v1")
stats_bp.before_request(check_api_key)


@stats_bp.route("/stats", methods=["GET"])
def get_stats():
    try:
        stats = get_tracker().get_learning_stats()
        today = get_tracker().get_learning_today()
        return jsonify({"success": True, "data": {"stats": stats, "today": today}})
    except Exception as e:
        logger.error(f"get_stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@stats_bp.route("/stats/trend", methods=["GET"])
def get_stats_trend():
    """Real per-day time-series (reviews, accuracy, additions, mastery, due).

    Backs the Overview page sparklines Ã¢â‚¬â€ these replace the previously random,
    fabricated trend data with values derived from stored timestamps.
    """
    try:
        days = int(request.args.get("days", 7))
        if not (1 <= days <= GRAPH_GAPS_MAX_DAYS):
            return jsonify({"success": False, "error": "days must be 1Ã¢â‚¬â€œ90"}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "days must be an integer"}), 400
    try:
        from tracker_app.db import models
        from tracker_app.db.repository import LearningRepository

        with models.SessionLocal() as db:
            trend = LearningRepository.get_review_trend(db, days=days)
        return jsonify({"success": True, "data": trend})
    except Exception as e:
        logger.error(f"get_stats_trend: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@stats_bp.route("/tracking/history", methods=["DELETE"])
def delete_tracking_history():
    """Clear the passive capture trail: sessions, multimodal logs, memory
    decay, metrics, daily summaries, and intent history Ã¢â‚¬â€ while KEEPING the
    explicit learning deck (learning_items) intact."""
    try:
        from tracker_app.db.models import (
            SessionLocal,
            TrackingSession,
            MultiModalLog,
            MemoryDecay,
            Metric,
            DailySummary,
            IntentPrediction,
            IntentAccuracy,
            FeedbackTrainingSample,
            ConceptEncounter,
        )
        from sqlalchemy import delete

        with SessionLocal() as db:
            n_enc = db.execute(delete(ConceptEncounter)).rowcount
            db.execute(delete(TrackingSession))
            db.execute(delete(MultiModalLog))
            db.execute(delete(MemoryDecay))
            db.execute(delete(Metric))
            db.execute(delete(DailySummary))
            n_pred = db.execute(delete(IntentPrediction)).rowcount
            db.execute(delete(IntentAccuracy))
            db.execute(delete(FeedbackTrainingSample))
            db.commit()
        return jsonify(
            {
                "success": True,
                "message": "Tracking history cleared",
                "deleted_encounters": n_enc,
                "deleted_predictions": n_pred,
            }
        )
    except Exception as e:
        logger.error(f"delete_tracking_history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@stats_bp.route("/tracking/daily-summary", methods=["GET"])
def daily_summary():
    """Return daily summary for a given date (default: today)."""
    try:
        from tracker_app.tracking.activity_monitor import TrackingAnalytics

        date_str = request.args.get("date")
        date = None
        if date_str:
            try:
                date = datetime.fromisoformat(date_str)
            except ValueError:
                return jsonify({"success": False, "error": "Invalid date format, use ISO 8601"}), 400
        summary = TrackingAnalytics().get_daily_summary(date=date)
        return jsonify({"success": True, "data": summary})
    except Exception as e:
        logger.error("daily_summary: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@stats_bp.route("/tracking/trend-analysis", methods=["GET"])
def trend_analysis():
    """Return N-day tracking trend analysis."""
    try:
        from tracker_app.tracking.activity_monitor import TrackingAnalytics

        days = request.args.get("days", 7, type=int)
        if days < 1 or days > 365:
            return jsonify({"success": False, "error": "days must be 1-365"}), 400
        analysis = TrackingAnalytics().get_trend_analysis(days=days)
        return jsonify({"success": True, "data": analysis})
    except Exception as e:
        logger.error("trend_analysis: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@stats_bp.route("/stats/accuracy-today", methods=["GET"])
def accuracy_today():
    """Return today's review accuracy breakdown."""
    try:
        today_data = get_tracker().get_learning_today()
        return jsonify({"success": True, "data": today_data})
    except Exception as e:
        logger.error("accuracy_today: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
