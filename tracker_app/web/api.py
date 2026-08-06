"""Flask API: tracking, feedback/retraining, knowledge graph, micro-quiz, and ingest endpoints."""

import json
import threading
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from tracker_app.learning.learning_tracker import LearningTracker, DifficultyLevel, LearningItemType
from tracker_app.config import DATA_DIR

logger = logging.getLogger("API")

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# ── Singleton tracker (fixes double-instantiation) ────────────────────────────
_tracker: LearningTracker | None = None

def get_tracker() -> LearningTracker:
    global _tracker
    if _tracker is None:
        _tracker = LearningTracker()
    return _tracker

VALID_STATUSES = {'active', 'mastered', 'archived', 'all'}
MAX_LIMIT      = 500


# ══════════════════════════════════════════════════════════════════════════════
# FeedbackService  (business logic extracted from route handler)
# ══════════════════════════════════════════════════════════════════════════════

class FeedbackService:
    """Handles intent feedback recording and auto-retraining."""

    @staticmethod
    def record_feedback(prediction_id: int, is_correct: bool,
                        actual_intent: str | None = None) -> None:
        """Persist user feedback, update accuracy stats, save training sample."""
        from tracker_app.db.models import SessionLocal, FeedbackTrainingSample
        from tracker_app.db.repository import TrackingRepository, FeedbackRepository
        now = datetime.utcnow()
        with SessionLocal() as db:
            pred = TrackingRepository.get_intent_prediction(db, prediction_id)

            if pred:
                pred.user_feedback = 1 if is_correct else 0
                pred.feedback_timestamp = now

                if not is_correct and actual_intent:
                    pred.actual_intent = actual_intent
                    sample = FeedbackTrainingSample(
                        timestamp=now,
                        feature_vector=pred.context_keywords or "[]",
                        predicted_label=pred.predicted_intent or "unknown",
                        actual_label=actual_intent,
                        confidence=pred.confidence or 0.0,
                    )
                    FeedbackRepository.log_feedback_sample(db, sample)

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
                t = threading.Thread(
                    target=FeedbackService._retrain_from_feedback,
                    daemon=True, name="fkt-retrain"
                )
                t.start()
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
                log.info("Background retraining complete — model updated.")
            else:
                log.warning(f"Retraining failed: {result.stderr[:300]}")
        except Exception as e:
            log.error(f"Retraining error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Learning Items
# ══════════════════════════════════════════════════════════════════════════════

@api_bp.route('/items', methods=['GET'])
def get_items():
    try:
        limit = int(request.args.get('limit', 50))
        if not (1 <= limit <= MAX_LIMIT):
            return jsonify({'success': False, 'error': f'limit must be 1–{MAX_LIMIT}'}), 400
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

    question = data.get('question', '').strip()
    answer   = data.get('answer',   '').strip()

    if not question:
        return jsonify({'success': False, 'error': 'question is required'}), 400
    if not answer:
        return jsonify({'success': False, 'error': 'answer is required'}), 400
    if len(question) > 1000:
        return jsonify({'success': False, 'error': 'question must be under 1000 chars'}), 400

    difficulty = data.get('difficulty', 'medium')
    if difficulty not in {'easy', 'medium', 'hard'}:
        return jsonify({'success': False, 'error': 'difficulty must be easy/medium/hard'}), 400

    try:
        item_id = get_tracker().add_learning_item(
            question=question,
            answer=answer,
            difficulty=DifficultyLevel(difficulty).value,
            item_type=LearningItemType(data.get('item_type', 'concept')).value,
            tags=data.get('tags', []),
        )
        return jsonify({'success': True, 'data': {'id': item_id}}), 201
    except Exception as e:
        logger.error(f"create_item: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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


@api_bp.route('/reviews', methods=['POST'])
def record_review():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'Request body must be valid JSON'}), 400

    item_id = data.get('item_id', '').strip()
    if not item_id:
        return jsonify({'success': False, 'error': 'item_id is required'}), 400

    try:
        quality = int(data.get('quality', 3))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'quality must be an integer'}), 400

    if not (0 <= quality <= 5):
        return jsonify({'success': False, 'error': 'quality must be 0–5'}), 400

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
        return jsonify({'success': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# Intent & feedback retraining
# ══════════════════════════════════════════════════════════════════════════════

@api_bp.route('/intent/recent', methods=['GET'])
def get_recent_intent():
    from tracker_app.db.models import SessionLocal
    from tracker_app.db.repository import TrackingRepository
    try:
        with SessionLocal() as db:
            row = TrackingRepository.get_recent_intent_prediction(db)
            if not row:
                return jsonify({'success': True, 'data': None})
            ts = row.timestamp.isoformat() if isinstance(row.timestamp, datetime) else str(row.timestamp)
            return jsonify({'success': True, 'data': {
                'id': row.id, 'timestamp': ts,
                'predicted_intent': row.predicted_intent,
                'confidence': row.confidence,
                'user_feedback': row.user_feedback,
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
    if not data or 'prediction_id' not in data or 'is_correct' not in data:
        return jsonify({'success': False,
                        'error': 'prediction_id and is_correct are required'}), 400

    if not data['is_correct'] and 'actual_intent' not in data:
        return jsonify({'success': False,
                        'error': 'actual_intent required when is_correct=false'}), 400

    try:
        FeedbackService.record_feedback(
            prediction_id=int(data['prediction_id']),
            is_correct=bool(data['is_correct']),
            actual_intent=data.get('actual_intent'),
        )
        FeedbackService.maybe_trigger_retrain()
        return jsonify({'success': True, 'message': 'Feedback recorded'})
    except Exception as e:
        logger.error(f"send_intent_feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# Knowledge Graph
# ══════════════════════════════════════════════════════════════════════════════

@api_bp.route('/graph/stats', methods=['GET'])
def get_graph_stats():
    try:
        from tracker_app.tracking.knowledge_graph import get_graph_stats
        return jsonify({'success': True, 'data': get_graph_stats()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/graph/gaps', methods=['GET'])
def get_knowledge_gaps():
    try:
        from tracker_app.tracking.knowledge_graph import find_knowledge_gaps
        limit = int(request.args.get('limit', 5))
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
        from tracker_app.tracking.knowledge_graph import compute_concept_drift
        result = compute_concept_drift(concept, [])
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# Micro-Quiz
# ══════════════════════════════════════════════════════════════════════════════

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
    if not data or 'concept' not in data or 'was_correct' not in data:
        return jsonify({'success': False,
                        'error': 'concept and was_correct are required'}), 400
    try:
        from tracker_app.tracking.quiz_engine import record_quiz_result
        record_quiz_result(str(data['concept']), bool(data['was_correct']))
        return jsonify({'success': True, 'message': 'Quiz result recorded in SM-2'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# Browser Extension Ingestion
# ══════════════════════════════════════════════════════════════════════════════

@api_bp.route('/ingest', methods=['POST'])
def browser_ingest():
    """
    Receive text from the browser extension.
    Runs YAKE! keyword extraction + concept scheduling.
    Primary OCR alternative for web-based study sessions.
    """
    data = request.get_json(silent=True)
    if not data or 'text' not in data:
        return jsonify({'success': False, 'error': 'text field required'}), 400

    text  = str(data.get('text', ''))[:10000]
    title = str(data.get('title', ''))[:200]

    if len(text.strip()) < 20:
        return jsonify({'success': True, 'message': 'Text too short — skipped'})

    try:
        from tracker_app.tracking.keyword_extractor import get_keyword_extractor
        from tracker_app.learning.concept_scheduler import ConceptScheduler
        from tracker_app.learning.text_quality_validator import validate_and_clean_extraction

        validation = validate_and_clean_extraction(text)
        if not validation.get('is_useful', False):
            return jsonify({'success': True, 'message': 'Text filtered as low quality'})

        extractor = get_keyword_extractor()
        keywords  = extractor.get_keyword_scores_dict(
            validation['cleaned_text'], top_n=15
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
                )
                if result:
                    saved += 1

        return jsonify({
            'success':        True,
            'concepts_saved': saved,
            'keywords':       list(keywords.keys())[:5],
        })
    except Exception as e:
        logger.error(f"browser_ingest: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# Study Sessions (Phase 9 — session-gated concept capture)
# ══════════════════════════════════════════════════════════════════════════════

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
    """Toggle a study session on — the tracker loop only captures concepts
    while a session is active."""
    try:
        from tracker_app.tracking.session_state import start
        return jsonify({'success': True, 'data': start()})
    except Exception as e:
        logger.error(f"start_study_session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/session/stop', methods=['POST'])
def stop_study_session():
    """Toggle a study session off — capture pauses and analytics are saved."""
    try:
        from tracker_app.tracking.session_state import stop
        return jsonify({'success': True, 'data': stop()})
    except Exception as e:
        logger.error(f"stop_study_session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# Health check
# ══════════════════════════════════════════════════════════════════════════════

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
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0.0',
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
