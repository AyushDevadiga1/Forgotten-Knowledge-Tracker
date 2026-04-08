# web/api.py — FKT 2.0 Phase 9 (Self-Improving Model) + Phase 6/7 endpoints
# Added:
#   - /intent/feedback stores FeedbackTrainingSample + triggers auto-retrain
#   - /graph/stats, /graph/gaps (Phase 6 knowledge graph)
#   - /quiz/current, /quiz/answer (Phase 7 micro-quiz)
#   - /ingest (Phase 10 browser extension)
#   - Singleton LearningTracker (fixes double-instantiation)
#   - realtime.py N+1 fix applied here too

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
# Intent — Phase 9 self-improving model
# ══════════════════════════════════════════════════════════════════════════════

@api_bp.route('/intent/recent', methods=['GET'])
def get_recent_intent():
    from tracker_app.db.models import SessionLocal, IntentPrediction
    try:
        with SessionLocal() as db:
            row = (db.query(IntentPrediction)
                     .order_by(IntentPrediction.timestamp.desc())
                     .first())
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
      2. Triggers background retraining after every 50 corrections (Phase 9)
    """
    data = request.get_json(silent=True)
    if not data or 'prediction_id' not in data or 'is_correct' not in data:
        return jsonify({'success': False,
                        'error': 'prediction_id and is_correct are required'}), 400

    if not data['is_correct'] and 'actual_intent' not in data:
        return jsonify({'success': False,
                        'error': 'actual_intent required when is_correct=false'}), 400

    try:
        from tracker_app.db.models import (
            SessionLocal, IntentPrediction, IntentAccuracy, FeedbackTrainingSample
        )
        with SessionLocal() as db:
            pred = db.query(IntentPrediction).filter(
                IntentPrediction.id == int(data['prediction_id'])
            ).first()

            if pred:
                if data['is_correct']:
                    pred.user_feedback = 1
                    pred.feedback_timestamp = datetime.utcnow()
                else:
                    pred.user_feedback = 0
                    pred.feedback_timestamp = datetime.utcnow()
                    actual = str(data['actual_intent'])
                    pred.actual_intent = actual

                    # Save feedback sample for Phase 9 retraining
                    sample = FeedbackTrainingSample(
                        timestamp=datetime.utcnow(),
                        feature_vector=pred.context_keywords or "[]",
                        predicted_label=pred.predicted_intent or "unknown",
                        actual_label=actual,
                        confidence=pred.confidence or 0.0,
                    )
                    db.add(sample)

                # Update accuracy stats
                intent = pred.predicted_intent or "unknown"
                acc = db.query(IntentAccuracy).filter(
                    IntentAccuracy.intent == intent
                ).first()
                if acc is None:
                    acc = IntentAccuracy(
                        intent=intent,
                        total_predictions=1,
                        correct_predictions=1 if data['is_correct'] else 0,
                    )
                    db.add(acc)
                else:
                    acc.total_predictions += 1
                    if data['is_correct']:
                        acc.correct_predictions += 1
                    acc.accuracy = acc.correct_predictions / acc.total_predictions
                    acc.last_updated = datetime.utcnow()

                db.commit()

        # Phase 9: trigger retraining every 50 feedback samples
        _maybe_trigger_retrain()

        return jsonify({'success': True, 'message': 'Feedback recorded'})
    except Exception as e:
        logger.error(f"send_intent_feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _maybe_trigger_retrain():
    """Trigger background retraining after every 50 user corrections."""
    try:
        from tracker_app.db.models import SessionLocal, FeedbackTrainingSample
        with SessionLocal() as db:
            count = db.query(FeedbackTrainingSample).count()
        if count > 0 and count % 50 == 0:
            t = threading.Thread(target=_retrain_from_feedback, daemon=True, name="fkt-retrain")
            t.start()
            logger.info(f"Auto-retrain triggered at {count} feedback samples.")
    except Exception as e:
        logger.debug(f"_maybe_trigger_retrain: {e}")


def _retrain_from_feedback():
    """Background retraining from user corrections. Replaces model if improved."""
    import subprocess, sys
    from pathlib import Path
    log = logging.getLogger("AutoRetrain")
    log.info("Background retraining started...")
    try:
        root   = Path(__file__).parent.parent.parent
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
# Knowledge Graph — Phase 6
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
# Micro-Quiz — Phase 7
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
# Browser Extension Ingestion — Phase 10
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
                scheduler.add_concept(
                    concept=concept,
                    confidence=float(score),
                    context=f"browser:{title[:80]}",
                    attention_at_encoding=60.0,  # assume moderate engagement
                )
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
# Health check
# ══════════════════════════════════════════════════════════════════════════════

@api_bp.route('/health', methods=['GET'])
def health_check():
    try:
        from tracker_app.db.models import SessionLocal, LearningItem, FeedbackTrainingSample
        with SessionLocal() as db:
            item_count     = db.query(LearningItem).count()
            feedback_count = db.query(FeedbackTrainingSample).count()
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
