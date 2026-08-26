"""Telemetry dashboard endpoints."""

import json
import logging
from collections import Counter
from datetime import timedelta

from flask import Blueprint, jsonify

from tracker_app.db import models
from tracker_app.db.models import MultiModalLog, IntentAccuracy
from tracker_app.web.shared import check_api_key
from tracker_app.utils import utcnow as _utcnow

logger = logging.getLogger("API")

telemetry_bp = Blueprint("telemetry", __name__, url_prefix="/api/v1")
telemetry_bp.before_request(check_api_key)


@telemetry_bp.route("/telemetry/summary", methods=["GET"])
def get_telemetry_summary():
    """Aggregated telemetry summary for the dashboard."""
    try:
        with models.SessionLocal() as db:
            now = _utcnow()
            day_ago = now - timedelta(hours=24)

            logs = (
                db.query(MultiModalLog)
                .filter(MultiModalLog.timestamp >= day_ago)
                .order_by(MultiModalLog.timestamp.asc())
                .all()
            )

            # Attention time series (10-min buckets)
            attention_series = []
            bucket_size = timedelta(minutes=10)
            current_bucket = day_ago
            bucket_vals = []
            for log in logs:
                if log.timestamp >= current_bucket + bucket_size:
                    if bucket_vals:
                        attention_series.append({
                            "t": current_bucket.isoformat(),
                            "v": round(sum(bucket_vals) / len(bucket_vals), 1),
                        })
                    bucket_vals = []
                    current_bucket = log.timestamp.replace(second=0, microsecond=0)
                    current_bucket = current_bucket.replace(
                        minute=(current_bucket.minute // 10) * 10
                    )
                if log.attention_score is not None:
                    bucket_vals.append(log.attention_score)
            if bucket_vals:
                attention_series.append({
                    "t": current_bucket.isoformat(),
                    "v": round(sum(bucket_vals) / len(bucket_vals), 1),
                })

            # Intent distribution
            intent_counter = Counter()
            for log in logs:
                if log.intent_label:
                    intent_counter[log.intent_label] += 1
            intent_distribution = [
                {"label": k, "count": v}
                for k, v in intent_counter.most_common(10)
            ]

            # Top OCR keywords
            keyword_counter = Counter()
            for log in logs:
                if log.ocr_keywords:
                    try:
                        kw = json.loads(log.ocr_keywords) if isinstance(log.ocr_keywords, str) else log.ocr_keywords
                        if isinstance(kw, dict):
                            keyword_counter.update(kw.keys())
                        elif isinstance(kw, list):
                            keyword_counter.update(kw)
                    except (json.JSONDecodeError, TypeError):
                        pass
            top_keywords = [
                {"keyword": k, "count": v}
                for k, v in keyword_counter.most_common(15)
            ]

            # Audio label distribution
            audio_counter = Counter()
            for log in logs:
                if log.audio_label:
                    audio_counter[log.audio_label] += 1
            audio_distribution = [
                {"label": k, "count": v}
                for k, v in audio_counter.most_common(10)
            ]

            # Window time breakdown
            window_counter = Counter()
            for log in logs:
                if log.window_title and log.window_title != "Unknown":
                    window_counter[log.window_title] += 1
            top_windows = [
                {"window": k, "count": v}
                for k, v in window_counter.most_common(10)
            ]

            # Intent accuracy
            accuracies = db.query(IntentAccuracy).all()
            intent_accuracy = [
                {
                    "intent": a.intent,
                    "accuracy": round(a.accuracy * 100, 1) if a.accuracy else 0,
                    "total": a.total_predictions,
                }
                for a in accuracies
            ]

            return jsonify({
                "success": True,
                "data": {
                    "attention_series": attention_series,
                    "intent_distribution": intent_distribution,
                    "top_keywords": top_keywords,
                    "audio_distribution": audio_distribution,
                    "top_windows": top_windows,
                    "intent_accuracy": intent_accuracy,
                    "total_logs": len(logs),
                },
            })
    except Exception as e:
        logger.error(f"telemetry_summary: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
