"""Intent prediction endpoints, user feedback recording, and auto-retraining."""

import json
import logging
import threading
from datetime import datetime

from flask import Blueprint, jsonify, request

from tracker_app.utils import utcnow as _utcnow
from tracker_app.constants import RETRAIN_EVERY_N, RETRAIN_TIMEOUT
from tracker_app.web.shared import _parse_bool_flag, check_api_key
from tracker_app.web import shared

logger = logging.getLogger("API")

intent_bp = Blueprint("intent", __name__, url_prefix="/api/v1")
intent_bp.before_request(check_api_key)


# ---------------------------------------------------------------------------
# FeedbackService  (business logic extracted from route handler)
# ---------------------------------------------------------------------------


class FeedbackService:
    """Handles intent feedback recording and auto-retraining."""

    @staticmethod
    def record_feedback(prediction_id: int, is_correct: bool, actual_intent: str | None = None) -> None:
        """Persist user feedback, update accuracy stats, save training sample."""
        from tracker_app.db.models import SessionLocal, FeedbackTrainingSample
        from tracker_app.db.repository import TrackingRepository, FeedbackRepository

        now = _utcnow()
        with SessionLocal() as db:
            pred = TrackingRepository.get_intent_prediction(db, prediction_id)

            if pred:
                pred.user_feedback = 1 if is_correct else 0
                pred.feedback_timestamp = now

                if not is_correct and actual_intent:
                    pred.actual_intent = actual_intent

                    # FKT-F-005: only persist a training sample when the stored
                    # feature vector is valid JSON AND a 6-element list. Legacy
                    # rows (e.g. window titles stored in context_keywords) must
                    # never be forwarded into the training pipeline; the
                    # correction itself is still recorded above.
                    valid_vector = False
                    try:
                        parsed = json.loads(pred.context_keywords or "[]")
                        valid_vector = isinstance(parsed, list) and len(parsed) == 6
                    except (json.JSONDecodeError, TypeError):
                        valid_vector = False

                    if valid_vector:
                        sample = FeedbackTrainingSample(
                            timestamp=now,
                            feature_vector=pred.context_keywords or "[]",
                            predicted_label=pred.predicted_intent or "unknown",
                            actual_label=actual_intent,
                            confidence=pred.confidence or 0.0,
                            window_title=pred.window_title or "",
                        )
                        FeedbackRepository.log_feedback_sample(db, sample)
                    else:
                        logger.warning(
                            f"record_feedback: skipping FeedbackTrainingSample for prediction "
                            f"{prediction_id} Ã¢â‚¬â€ context_keywords is not a JSON 6-element "
                            f"feature vector; user feedback still recorded"
                        )

                intent = pred.predicted_intent or "unknown"
                TrackingRepository.update_intent_accuracy(db, intent, is_correct)

    @staticmethod
    def maybe_trigger_retrain() -> None:
        """Trigger background retraining after every 50 user corrections."""
        try:
            from tracker_app.db.models import SessionLocal
            from tracker_app.db.repository import FeedbackRepository

            with SessionLocal() as db:
                count = FeedbackRepository.get_total_count(db)
            if count > 0 and count % RETRAIN_EVERY_N == 0:
                if not shared._retrain_lock.acquire(blocking=False):
                    logger.info("Auto-retrain skipped: a retraining run is already active.")
                    return
                try:
                    t = threading.Thread(target=FeedbackService._retrain_from_feedback, daemon=True, name="fkt-retrain")
                    t.start()
                except Exception:
                    shared._retrain_lock.release()
                    raise
                logger.info(f"Auto-retrain triggered at {count} feedback samples.")
        except Exception as e:
            logger.debug(f"maybe_trigger_retrain: {e}")

    @staticmethod
    def _retrain_from_feedback() -> None:
        """Background retraining from user corrections. Replaces model if improved."""
        import subprocess
        import sys
        from pathlib import Path

        log = logging.getLogger("AutoRetrain")
        log.info("Background retraining started...")
        try:
            root = Path(__file__).parent.parent.parent.parent
            result = subprocess.run(
                [sys.executable, "-m", "tracker_app.scripts.train_models_from_logs", "--include-feedback"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=RETRAIN_TIMEOUT,
            )
            if result.returncode == 0:
                log.info("Background retraining complete Ã¢â‚¬â€ model updated.")
            else:
                log.warning(f"Retraining failed: {result.stderr[:300]}")
        except Exception as e:
            log.error(f"Retraining error: {e}")
        finally:
            shared._retrain_lock.release()


@intent_bp.route("/intent/recent", methods=["GET"])
def get_recent_intent():
    """Return the next feedback-promptable prediction, or null.

    Rate-limited so the toast can't nag every cycle: a row is only surfaced when
    it is unanswered (no user_feedback), has never been shown (no prompted_at),
    and at least TOAST_COOLDOWN_MINUTES have passed since the last prompt. When
    returned, the row is stamped prompted_at so it is never shown twice.
    """
    from datetime import timedelta
    from sqlalchemy import update
    from tracker_app.config import TOAST_COOLDOWN_MINUTES
    from tracker_app.db.models import SessionLocal, IntentPrediction
    from tracker_app.db.repository import TrackingRepository

    try:
        with SessionLocal() as db:
            row = TrackingRepository.get_recent_intent_prediction(db)
            if not row:
                return jsonify({"success": True, "data": None})

            if row.user_feedback is not None or row.prompted_at is not None:
                return jsonify({"success": True, "data": None})

            last_prompt = (
                db.query(IntentPrediction.prompted_at)
                .filter(IntentPrediction.prompted_at.isnot(None))
                .order_by(IntentPrediction.prompted_at.desc())
                .first()
            )
            if last_prompt and last_prompt[0] is not None and _utcnow() - last_prompt[0] < timedelta(minutes=TOAST_COOLDOWN_MINUTES):
                    return jsonify({"success": True, "data": None})

            now = _utcnow()
            # Atomic claim: the conditional UPDATE flips prompted_at from NULL,
            # and only one concurrent request can do that. A second request that
            # read the same eligible row (the TOCTOU window) gets rowcount 0 and
            # returns null instead of double-firing the toast.
            result = db.execute(
                update(IntentPrediction)
                .where(
                    IntentPrediction.id == row.id,
                    IntentPrediction.prompted_at.is_(None),
                    IntentPrediction.user_feedback.is_(None),
                )
                .values(prompted_at=now)
            )
            db.commit()
            if result.rowcount == 0:
                return jsonify({"success": True, "data": None})

            ts = row.timestamp.isoformat() if isinstance(row.timestamp, datetime) else str(row.timestamp)
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "id": row.id,
                        "timestamp": ts,
                        "predicted_intent": row.predicted_intent,
                        "confidence": row.confidence,
                        "user_feedback": row.user_feedback,
                        "window_title": row.window_title or "",
                    },
                }
            )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@intent_bp.route("/intent/feedback", methods=["POST"])
def send_intent_feedback():
    """
    Record user feedback. When is_correct=False and actual_intent is provided:
      1. Saves a FeedbackTrainingSample row
      2. Triggers background retraining after every 50 corrections
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Request body must be valid JSON"}), 400
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400
    if "prediction_id" not in data or "is_correct" not in data:
        return jsonify({"success": False, "error": "prediction_id and is_correct are required"}), 400

    is_correct = _parse_bool_flag(data["is_correct"])
    if is_correct is None:
        return jsonify({"success": False, "error": "is_correct must be a boolean"}), 400

    if not is_correct and "actual_intent" not in data:
        return jsonify({"success": False, "error": "actual_intent required when is_correct=false"}), 400

    try:
        prediction_id = int(data["prediction_id"])
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "prediction_id must be an integer"}), 400

    try:
        FeedbackService.record_feedback(
            prediction_id=prediction_id,
            is_correct=is_correct,
            actual_intent=data.get("actual_intent"),
        )
        FeedbackService.maybe_trigger_retrain()
        return jsonify({"success": True, "message": "Feedback recorded"})
    except Exception as e:
        logger.error(f"send_intent_feedback: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@intent_bp.route("/intent/predictions", methods=["DELETE"])
def delete_intent_predictions():
    """Clear all raw intent predictions, accuracy counters, and feedback
    training samples (the passive capture trail)."""
    try:
        from tracker_app.db.models import (
            SessionLocal,
            IntentPrediction,
            IntentAccuracy,
            FeedbackTrainingSample,
        )
        from sqlalchemy import delete

        with SessionLocal() as db:
            n_pred = db.execute(delete(IntentPrediction)).rowcount
            db.execute(delete(IntentAccuracy))
            n_fb = db.execute(delete(FeedbackTrainingSample)).rowcount
            db.commit()
        return jsonify(
            {
                "success": True,
                "message": "Intent history cleared",
                "deleted_predictions": n_pred,
                "deleted_feedback": n_fb,
            }
        )
    except Exception as e:
        logger.error(f"delete_intent_predictions: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@intent_bp.route("/intent/stats", methods=["GET"])
def intent_stats():
    """Return aggregated intent accuracy statistics."""
    try:
        from tracker_app.tracking.activity_monitor import IntentValidator
        stats = IntentValidator().get_accuracy_stats()
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        logger.error("intent_stats: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
