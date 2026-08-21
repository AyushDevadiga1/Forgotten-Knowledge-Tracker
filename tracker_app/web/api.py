"""Flask API: tracking, feedback/retraining, knowledge graph, micro-quiz, and ingest endpoints."""

import json
import os
import re
import threading
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from tracker_app.utils import utcnow as _utcnow

from tracker_app.learning.learning_tracker import LearningTracker, DifficultyLevel, LearningItemType
from tracker_app.config import DATA_DIR

logger = logging.getLogger("API")

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


@api_bp.before_request
def check_api_key():
    """Require API key on all endpoints except health and static."""
    if request.endpoint in ('api.health_check',):
        return None
    api_key = os.environ.get('API_KEY', '')
    if not api_key:
        return None  # auth disabled (dev mode)
    provided = request.headers.get('X-API-Key', '')
    if not provided or provided != api_key:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    return None

# C-2: only one background retraining subprocess may run at a time â€” two
# concurrent writes to models/intent_classifier.pkl corrupt the pickle.
_retrain_lock = threading.Lock()

# Ã¢â€â‚¬Ã¢â€â‚¬ Singleton tracker (fixes double-instantiation) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
_tracker: LearningTracker | None = None

def get_tracker() -> LearningTracker:
    global _tracker
    if _tracker is None:
        _tracker = LearningTracker()
    return _tracker

VALID_STATUSES = {'active', 'mastered', 'archived', 'all'}
MAX_LIMIT      = 500


def _parse_bool_flag(value):
    """Strictly parse a JSON boolean-ish flag.

    Accepts real JSON booleans plus the common string/number forms
    'true'/'false' (case-insensitive, '1'/'0'). Returns None for anything
    unrecognised so callers can reject it with a 400 instead of silently
    treating a value like the string "false" as True (bool("false") is True).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ('true', '1'):
            return True
        if v in ('false', '0'):
            return False
        return None
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    return None


_CONTROL_CHARS_RE = re.compile(r'[\x00-\x1f\x7f-\x9f]')


def _sanitize_title(raw) -> str:
    """Strip C0/C1 control characters and collapse whitespace (F-2).

    Browser extensions have shipped titles containing escape sequences,
    null bytes, and newlines. Those reach ConceptEncounter.context_snippet
    and later render as raw control bytes in the UI. Printable Unicode is
    preserved; control runs and stray whitespace are removed/collapsed.
    """
    if not raw:
        return ""
    cleaned = _CONTROL_CHARS_RE.sub('', str(raw))
    return ' '.join(cleaned.split())


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# FeedbackService  (business logic extracted from route handler)
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

class FeedbackService:
    """Handles intent feedback recording and auto-retraining."""

    @staticmethod
    def record_feedback(prediction_id: int, is_correct: bool,
                        actual_intent: str | None = None) -> None:
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
                            f"{prediction_id} â€” context_keywords is not a JSON 6-element "
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
            if count > 0 and count % 50 == 0:
                if not _retrain_lock.acquire(blocking=False):
                    logger.info("Auto-retrain skipped: a retraining run is already active.")
                    return
                try:
                    t = threading.Thread(
                        target=FeedbackService._retrain_from_feedback,
                        daemon=True, name="fkt-retrain"
                    )
                    t.start()
                except Exception:
                    _retrain_lock.release()
                    raise
                logger.info(f"Auto-retrain triggered at {count} feedback samples.")
        except Exception as e:
            logger.debug(f"maybe_trigger_retrain: {e}")

    @staticmethod
    def _retrain_from_feedback() -> None:
        """Background retraining from user corrections. Replaces model if improved."""
        import subprocess, sys
        from pathlib import Path
        log = logging.getLogger("AutoRetrain")
        log.info("Background retraining started...")
        try:
            root = Path(__file__).parent.parent.parent
            result = subprocess.run(
                [sys.executable, "-m", "tracker_app.scripts.train_models_from_logs",
                 "--include-feedback"],
                cwd=str(root), capture_output=True, text=True, timeout=180
            )
            if result.returncode == 0:
                log.info("Background retraining complete â€” model updated.")
            else:
                log.warning(f"Retraining failed: {result.stderr[:300]}")
        except Exception as e:
            log.error(f"Retraining error: {e}")
        finally:
            _retrain_lock.release()


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# Learning Items
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

@api_bp.route('/items', methods=['GET'])
def get_items():
    try:
        limit = int(request.args.get('limit', 50))
        if not (1 <= limit <= MAX_LIMIT):
            return jsonify({'success': False, 'error': f'limit must be 1â€“{MAX_LIMIT}'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'limit must be an integer'}), 400

    status = request.args.get('status', 'active')
    if status not in VALID_STATUSES:
        return jsonify({'success': False,
                        'error': f'status must be one of: {sorted(VALID_STATUSES)}'}), 400
    try:
        items = get_tracker().get_items(status=status, limit=limit)
        return jsonify({'success': True, 'data': items, 'count': len(items)})
    except Exception as e:
        logger.error(f"get_items: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@api_bp.route('/items', methods=['POST'])
def create_item():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'Request body must be valid JSON'}), 400
    if not isinstance(data, dict):
        return jsonify({'success': False, 'error': 'Request body must be a JSON object'}), 400

    question = data.get('question', '') or ''
    answer   = data.get('answer', '') or ''
    if not isinstance(question, str):
        question = str(question)   # JSON numbers must not crash .strip()
    if not isinstance(answer, str):
        answer = str(answer)
    question = question.strip()
    answer   = answer.strip()

    if not question:
        return jsonify({'success': False, 'error': 'question is required'}), 400
    if not answer:
        return jsonify({'success': False, 'error': 'answer is required'}), 400
    if len(question) > 1000:
        return jsonify({'success': False, 'error': 'question must be under 1000 chars'}), 400

    difficulty = data.get('difficulty', 'medium')
    if difficulty not in {'easy', 'medium', 'hard'}:
        return jsonify({'success': False, 'error': 'difficulty must be easy/medium/hard'}), 400

    item_type = data.get('item_type', 'concept')
    valid_item_types = {t.value for t in LearningItemType}
    if item_type not in valid_item_types:
        return jsonify({'success': False, 'error': 'item_type must be one of: '
                        + ', '.join(sorted(valid_item_types))}), 400

    try:
        item_id = get_tracker().add_learning_item(
            question=question,
            answer=answer,
            difficulty=DifficultyLevel(difficulty).value,
            item_type=LearningItemType(item_type).value,
            tags=data.get('tags', []),
        )
        return jsonify({'success': True, 'data': {'id': item_id}}), 201
    except Exception as e:
        logger.error(f"create_item: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/items/backfill', methods=['POST'])
def backfill_items():
    """One-shot migration: promote validated extracted concepts from
    tracked_concepts into the SM-2 learning deck. Idempotent â€” concepts with
    an existing deck item (exact question match) are skipped."""
    try:
        from tracker_app.learning.concept_promotion import backfill_items as run_backfill
        min_frequency = request.args.get('min_frequency', 3)
        try:
            min_frequency = int(min_frequency)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'min_frequency must be an integer'}), 400
        if not (1 <= min_frequency <= 1000):
            return jsonify({'success': False, 'error': 'min_frequency must be 1â€“1000'}), 400
        result = run_backfill(min_frequency=min_frequency)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"backfill_items: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@api_bp.route('/items/due', methods=['GET'])
def get_due_items():
    try:
        items = get_tracker().get_items_due()
        return jsonify({'success': True, 'data': items, 'count': len(items)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/items/<item_id>', methods=['GET'])
def get_item(item_id):
    try:
        item = get_tracker().get_item(item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404
        return jsonify({'success': True, 'data': item})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/items/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    """Permanently remove a learning item and its review history."""
    try:
        deleted = get_tracker().delete_item(item_id)
        if not deleted:
            return jsonify({'success': False, 'error': 'Item not found'}), 404
        return jsonify({'success': True, 'message': 'Item deleted'})
    except Exception as e:
        logger.error(f"delete_item: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/concepts/<concept>', methods=['DELETE'])
def delete_concept(concept):
    """Permanently remove a tracked concept, its encounter history, and its
    knowledge-graph node. This is the right-to-be-forgotten path for anything
    passively captured (e.g. a stray sensitive term)."""
    try:
        from tracker_app.db.models import SessionLocal, TrackedConcept
        from tracker_app.tracking.knowledge_graph import remove_concept_from_graph
        with SessionLocal() as db:
            row = db.query(TrackedConcept).filter(
                TrackedConcept.concept == concept).first()
            if not row:
                return jsonify({'success': False, 'error': 'Concept not found'}), 404
            db.delete(row)  # ConceptEncounter rows cascade via ORM
            db.commit()
        remove_concept_from_graph(concept)
        return jsonify({'success': True, 'message': 'Concept deleted'})
    except Exception as e:
        logger.error(f"delete_concept: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/intent/predictions', methods=['DELETE'])
def delete_intent_predictions():
    """Clear all raw intent predictions, accuracy counters, and feedback
    training samples (the passive capture trail)."""
    try:
        from tracker_app.db.models import (
            SessionLocal, IntentPrediction, IntentAccuracy,
            FeedbackTrainingSample,
        )
        from sqlalchemy import delete
        with SessionLocal() as db:
            n_pred  = db.execute(delete(IntentPrediction)).rowcount
            db.execute(delete(IntentAccuracy))
            n_fb    = db.execute(delete(FeedbackTrainingSample)).rowcount
            db.commit()
        return jsonify({'success': True, 'message': 'Intent history cleared',
                        'deleted_predictions': n_pred,
                        'deleted_feedback': n_fb})
    except Exception as e:
        logger.error(f"delete_intent_predictions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/tracking/history', methods=['DELETE'])
def delete_tracking_history():
    """Clear the passive capture trail: sessions, multimodal logs, memory
    decay, metrics, daily summaries, and intent history â€” while KEEPING the
    explicit learning deck (learning_items) intact."""
    try:
        from tracker_app.db.models import (
            SessionLocal, TrackingSession, MultiModalLog, MemoryDecay,
            Metric, DailySummary, IntentPrediction, IntentAccuracy,
            FeedbackTrainingSample, ConceptEncounter,
        )
        from sqlalchemy import delete
        with SessionLocal() as db:
            n_enc    = db.execute(delete(ConceptEncounter)).rowcount
            db.execute(delete(TrackingSession))
            db.execute(delete(MultiModalLog))
            db.execute(delete(MemoryDecay))
            db.execute(delete(Metric))
            db.execute(delete(DailySummary))
            n_pred   = db.execute(delete(IntentPrediction)).rowcount
            db.execute(delete(IntentAccuracy))
            db.execute(delete(FeedbackTrainingSample))
            db.commit()
        return jsonify({'success': True, 'message': 'Tracking history cleared',
                        'deleted_encounters': n_enc,
                        'deleted_predictions': n_pred})
    except Exception as e:
        logger.error(f"delete_tracking_history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/reviews', methods=['POST'])
def record_review():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'Request body must be valid JSON'}), 400
    if not isinstance(data, dict):
        return jsonify({'success': False, 'error': 'Request body must be a JSON object'}), 400

    item_id = data.get('item_id', '')
    if item_id is None:
        return jsonify({'success': False, 'error': 'item_id is required'}), 400
    if not isinstance(item_id, str):
        item_id = str(item_id)   # JSON numbers are valid ids â€” never crash on .strip()
    item_id = item_id.strip()
    if not item_id:
        return jsonify({'success': False, 'error': 'item_id is required'}), 400

    try:
        quality = int(data.get('quality', 3))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'quality must be an integer'}), 400

    if not (0 <= quality <= 5):
        return jsonify({'success': False, 'error': 'quality must be 0â€“5'}), 400

    try:
        get_tracker().record_review(item_id=item_id, quality_rating=quality)
        return jsonify({'success': True, 'message': 'Review recorded'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@api_bp.route('/stats', methods=['GET'])
def get_stats():
    try:
        stats = get_tracker().get_learning_stats()
        today = get_tracker().get_learning_today()
        return jsonify({'success': True, 'data': {'stats': stats, 'today': today}})
    except Exception as e:
        logger.error(f"get_stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/stats/trend', methods=['GET'])
def get_stats_trend():
    """Real per-day time-series (reviews, accuracy, additions, mastery, due).

    Backs the Overview page sparklines â€” these replace the previously random,
    fabricated trend data with values derived from stored timestamps.
    """
    try:
        days = int(request.args.get('days', 7))
        if not (1 <= days <= 90):
            return jsonify({'success': False, 'error': 'days must be 1â€“90'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'days must be an integer'}), 400
    try:
        from tracker_app.db import models
        from tracker_app.db.repository import LearningRepository
        with models.SessionLocal() as db:
            trend = LearningRepository.get_review_trend(db, days=days)
        return jsonify({'success': True, 'data': trend})
    except Exception as e:
        logger.error(f"get_stats_trend: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# Intent & feedback retraining
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

@api_bp.route('/intent/recent', methods=['GET'])
def get_recent_intent():
    """Return the next feedback-promptable prediction, or null.

    Rate-limited so the toast can't nag every cycle: a row is only surfaced when
    it is unanswered (no user_feedback), has never been shown (no prompted_at),
    and at least TOAST_COOLDOWN_MINUTES have passed since the last prompt. When
    returned, the row is stamped prompted_at so it is never shown twice.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import update
    from tracker_app.config import TOAST_COOLDOWN_MINUTES
    from tracker_app.db.models import SessionLocal, IntentPrediction
    from tracker_app.db.repository import TrackingRepository
    try:
        with SessionLocal() as db:
            row = TrackingRepository.get_recent_intent_prediction(db)
            if not row:
                return jsonify({'success': True, 'data': None})

            if row.user_feedback is not None or row.prompted_at is not None:
                return jsonify({'success': True, 'data': None})

            last_prompt = db.query(IntentPrediction.prompted_at).filter(
                IntentPrediction.prompted_at.isnot(None)
            ).order_by(IntentPrediction.prompted_at.desc()).first()
            if last_prompt and last_prompt[0] is not None:
                if _utcnow() - last_prompt[0] < timedelta(minutes=TOAST_COOLDOWN_MINUTES):
                    return jsonify({'success': True, 'data': None})

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
                return jsonify({'success': True, 'data': None})

            ts = row.timestamp.isoformat() if isinstance(row.timestamp, datetime) else str(row.timestamp)
            return jsonify({'success': True, 'data': {
                'id': row.id, 'timestamp': ts,
                'predicted_intent': row.predicted_intent,
                'confidence': row.confidence,
                'user_feedback': row.user_feedback,
                'window_title': row.window_title or '',
            }})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/intent/feedback', methods=['POST'])
def send_intent_feedback():
    """
    Record user feedback. When is_correct=False and actual_intent is provided:
      1. Saves a FeedbackTrainingSample row
      2. Triggers background retraining after every 50 corrections
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False,
                        'error': 'Request body must be valid JSON'}), 400
    if not isinstance(data, dict):
        return jsonify({'success': False,
                        'error': 'Request body must be a JSON object'}), 400
    if 'prediction_id' not in data or 'is_correct' not in data:
        return jsonify({'success': False,
                        'error': 'prediction_id and is_correct are required'}), 400

    is_correct = _parse_bool_flag(data['is_correct'])
    if is_correct is None:
        return jsonify({'success': False,
                        'error': 'is_correct must be a boolean'}), 400

    if not is_correct and 'actual_intent' not in data:
        return jsonify({'success': False,
                        'error': 'actual_intent required when is_correct=false'}), 400

    try:
        prediction_id = int(data['prediction_id'])
    except (ValueError, TypeError):
        return jsonify({'success': False,
                        'error': 'prediction_id must be an integer'}), 400

    try:
        FeedbackService.record_feedback(
            prediction_id=prediction_id,
            is_correct=is_correct,
            actual_intent=data.get('actual_intent'),
        )
        FeedbackService.maybe_trigger_retrain()
        return jsonify({'success': True, 'message': 'Feedback recorded'})
    except Exception as e:
        logger.error(f"send_intent_feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# Knowledge Graph
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

@api_bp.route('/graph/stats', methods=['GET'])
def get_graph_stats():
    try:
        from tracker_app.tracking.knowledge_graph import get_graph_stats
        return jsonify({'success': True, 'data': get_graph_stats()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/graph/sync', methods=['POST'])
def sync_graph():
    """Force a knowledge-graph resync from the database (F-6).

    Loads the persisted graph if not already in memory, reconciles every
    concept from the DB, and returns the updated graph stats. Intended for
    after a bulk restore or when the graph is suspected to be stale.
    """
    try:
        from tracker_app.tracking.knowledge_graph import sync_db_to_graph
        return jsonify({'success': True, 'data': sync_db_to_graph(force=True)})
    except Exception as e:
        logger.error(f"sync_graph: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/graph/gaps', methods=['GET'])
def get_knowledge_gaps():
    try:
        from tracker_app.tracking.knowledge_graph import find_knowledge_gaps
        try:
            limit = int(request.args.get('limit', 5))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'limit must be an integer'}), 400
        if not (1 <= limit <= 50):
            return jsonify({'success': False, 'error': 'limit must be 1\u201350'}), 400
        gaps  = find_knowledge_gaps(top_k=limit)
        if gaps:
            from tracker_app.db.models import SessionLocal, TrackedConcept
            with SessionLocal() as db:
                rows = db.query(TrackedConcept).filter(
                    TrackedConcept.concept.in_([g['concept'] for g in gaps])
                ).all()
                last_seen = {r.concept: r.last_seen for r in rows}
            for g in gaps:
                ls = last_seen.get(g['concept'])
                g['last_seen'] = ls.isoformat() if ls else None
        return jsonify({'success': True, 'data': gaps, 'count': len(gaps)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/graph/drift/<concept>', methods=['GET'])
def get_concept_drift(concept):
    try:
        from tracker_app.tracking.knowledge_graph import (
            compute_concept_drift, get_session_concepts)
        keywords = get_session_concepts()
        result = compute_concept_drift(concept, keywords)
        result['session_keywords'] = keywords
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/graph/concept/<concept>', methods=['GET'])
def get_concept_detail(concept):
    """Live memory score + encounter history for a concept â€” backs the
    frontend's click-to-drill-in on a graph node."""
    try:
        from tracker_app.learning.concept_scheduler import ConceptScheduler
        from tracker_app.tracking.knowledge_graph import get_graph
        history = ConceptScheduler().get_concept_history(concept)
        memory = get_graph().nodes.get(concept, {}).get('memory_score', 0.5)
        return jsonify({'success': True, 'data': {
            'concept': concept,
            'memory_score': round(float(memory), 4),
            'history': history,
        }})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# Micro-Quiz
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

@api_bp.route('/quiz/current', methods=['GET'])
def get_current_quiz():
    try:
        from tracker_app.tracking.quiz_engine import generate_micro_quiz
        from tracker_app.tracking.knowledge_graph import get_graph
        quiz = generate_micro_quiz(get_graph())
        return jsonify({'success': True, 'data': quiz})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/quiz/answer', methods=['POST'])
def submit_quiz_answer():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False,
                        'error': 'Request body must be valid JSON'}), 400
    if not isinstance(data, dict):
        return jsonify({'success': False,
                        'error': 'Request body must be a JSON object'}), 400
    if 'concept' not in data or 'was_correct' not in data:
        return jsonify({'success': False,
                        'error': 'concept and was_correct are required'}), 400
    was_correct = _parse_bool_flag(data['was_correct'])
    if was_correct is None:
        return jsonify({'success': False,
                        'error': 'was_correct must be a boolean'}), 400
    try:
        from tracker_app.tracking.quiz_engine import record_quiz_result
        record_quiz_result(str(data['concept']), was_correct)
        return jsonify({'success': True, 'message': 'Quiz result recorded in SM-2'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# Browser Extension Ingestion
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

@api_bp.route('/ingest', methods=['POST'])
def browser_ingest():
    """
    Receive text from the browser extension.
    Runs YAKE! keyword extraction + concept scheduling.
    Primary OCR alternative for web-based study sessions.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'Request body must be valid JSON'}), 400
    if not isinstance(data, dict):
        return jsonify({'success': False, 'error': 'Request body must be a JSON object'}), 400
    if 'text' not in data:
        return jsonify({'success': False, 'error': 'text field required'}), 400

    text  = str(data.get('text', ''))[:10000]
    text_truncated = len(str(data.get('text', ''))) > 10000
    title = _sanitize_title(data.get('title', ''))[:200]

    if len(text.strip()) < 20:
        return jsonify({'success': True, 'message': 'Text too short â€” skipped'})

    try:
        from tracker_app.tracking.privacy_filter import (
            sanitize_text_for_storage, is_sensitive_window,
            strip_redaction_markers, filter_sensitive_keywords,
        )
        from tracker_app.tracking.keyword_extractor import extract_concepts
        from tracker_app.learning.concept_scheduler import ConceptScheduler
        from tracker_app.learning.text_quality_validator import validate_and_clean_extraction

        # Sensitive window title â†’ drop it (never stored as context).
        if is_sensitive_window(title):
            title = ""

        # Privacy gate FIRST â€” the extension path previously bypassed the
        # redactor entirely, so emails/passwords/SSNs reached add_concept.
        sanitized = sanitize_text_for_storage(text)
        if not sanitized['safe_to_store']:
            return jsonify({'success': True, 'message': 'Text filtered as sensitive'})

        text = strip_redaction_markers(sanitized['text'])

        validation = validate_and_clean_extraction(text)
        if not validation.get('is_useful', False):
            return jsonify({'success': True, 'message': 'Text filtered as low quality'})

        keywords = filter_sensitive_keywords(
            extract_concepts(validation['cleaned_text'], top_n=15)
        )

        if not keywords:
            return jsonify({'success': True, 'message': 'No keywords extracted'})

        scheduler = ConceptScheduler()
        saved     = 0
        for concept, score in keywords.items():
            if len(concept) >= 3:
                result = scheduler.add_concept(
                    concept=concept,
                    confidence=float(score),
                    context=f"browser:{title[:80]}",
                    attention_at_encoding=60.0,  # assume moderate engagement
                    source="browser_extension",
                )
                if result:
                    saved += 1

        return jsonify({
            'success':        True,
            'concepts_saved': saved,
            'keywords':       list(keywords.keys())[:5],
            'text_truncated': text_truncated,
        })
    except Exception as e:
        logger.error(f"browser_ingest: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# Study Sessions (Phase 9 â€” session-gated concept capture)
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

@api_bp.route('/session/status', methods=['GET'])
def get_session_status():
    """Return whether a study session is currently active and when it started."""
    try:
        from tracker_app.tracking.session_state import get_status
        return jsonify({'success': True, 'data': get_status()})
    except Exception as e:
        logger.error(f"get_session_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/session/start', methods=['POST'])
def start_study_session():
    """Toggle a study session on â€” the tracker loop only captures concepts
    while a session is active."""
    try:
        from tracker_app.tracking.session_state import start
        return jsonify({'success': True, 'data': start()})
    except Exception as e:
        logger.error(f"start_study_session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/session/stop', methods=['POST'])
def stop_study_session():
    """Toggle a study session off â€” capture pauses and analytics are saved."""
    try:
        from tracker_app.tracking.session_state import stop
        return jsonify({'success': True, 'data': stop()})
    except Exception as e:
        logger.error(f"stop_study_session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



# --- EAR Calibration ---

@api_bp.route('/session/calibrate', methods=['POST'])
def calibrate_session():
    """Trigger EAR calibration for the current session."""
    try:
        from tracker_app.config import CALIBRATION_DURATION_SECONDS
        from tracker_app.tracking.webcam_module import calibrate_ear
        from tracker_app.tracking.session_state import set_calibration
        duration = CALIBRATION_DURATION_SECONDS
        try:
            req = request.get_json(silent=True) or {}
            if 'duration_seconds' in req:
                duration = int(req['duration_seconds'])
        except Exception:
            pass
        result = calibrate_ear(duration)
        set_calibration(result)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error("calibrate_session: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500

# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# Health check
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

@api_bp.route('/health', methods=['GET'])
def health_check():
    try:
        from tracker_app.db.models import SessionLocal
        from tracker_app.db.repository import LearningRepository, FeedbackRepository
        with SessionLocal() as db:
            item_count     = LearningRepository.get_total_count(db)
            feedback_count = FeedbackRepository.get_total_count(db)
        return jsonify({
            'status': 'healthy',
            'timestamp': _utcnow().isoformat(),
            'version': '2.0.0',  # keep in sync with tracker_app.__version__
            'components': {
                'database':       'reachable',
                'item_count':     item_count,
                'feedback_count': feedback_count,
                'api':            'online',
            },
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
        }), 503

