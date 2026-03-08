"""
API Blueprint for Learning Items

RESTful API endpoints for managing learning items and reviews.
"""

import sqlite3
from contextlib import closing
from flask import Blueprint, request, jsonify
from datetime import datetime
from tracker_app.learning.learning_tracker import LearningTracker, DifficultyLevel, LearningItemType
from tracker_app.tracking.activity_monitor import IntentValidator
from tracker_app.config import DATA_DIR

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
tracker = LearningTracker()

VALID_STATUSES = {'active', 'mastered', 'archived', 'all'}
MAX_LIMIT = 500

@api_bp.route('/items', methods=['GET'])
def get_items():
    """Get all learning items with filtering"""
    # Validate limit
    try:
        limit = int(request.args.get('limit', 50))
        if limit <= 0 or limit > MAX_LIMIT:
            return jsonify({'success': False, 'error': f'limit must be between 1 and {MAX_LIMIT}'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'limit must be an integer'}), 400

    # Validate status
    status = request.args.get('status', 'active')
    if status not in VALID_STATUSES:
        return jsonify({'success': False, 'error': f'status must be one of: {sorted(VALID_STATUSES)}'}), 400

    try:
        items = tracker.get_items(status=status, limit=limit)
        return jsonify({'success': True, 'data': items, 'count': len(items)})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@api_bp.route('/items', methods=['POST'])
def create_item():
    """Create a new learning item"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'Request body must be valid JSON'}), 400

    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()

    if not question:
        return jsonify({'success': False, 'error': 'question is required and cannot be empty'}), 400
    if not answer:
        return jsonify({'success': False, 'error': 'answer is required and cannot be empty'}), 400
    if len(question) > 1000:
        return jsonify({'success': False, 'error': 'question must be under 1000 characters'}), 400

    difficulty = data.get('difficulty', 'medium')
    if difficulty not in {'easy', 'medium', 'hard'}:
        return jsonify({'success': False, 'error': 'difficulty must be easy, medium, or hard'}), 400

    try:
        difficulty_enum = DifficultyLevel(difficulty)
        item_type_enum = LearningItemType(data.get('item_type', 'concept'))
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid difficulty or item_type'}), 400

    try:
        item_id = tracker.add_learning_item(
            question=question,
            answer=answer,
            difficulty=difficulty_enum.value,
            item_type=item_type_enum.value,
            tags=data.get('tags', [])
        )
        return jsonify({'success': True, 'data': {'id': item_id}}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': f"Failed to create item: {str(e)}"}), 500

@api_bp.route('/items/<item_id>', methods=['GET'])
def get_item(item_id):
    """Get a specific learning item"""
    try:
        item = tracker.get_item(item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404
        
        return jsonify({
            'success': True,
            'data': item
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/items/due', methods=['GET'])
def get_due_items():
    """Get items due for review"""
    try:
        items = tracker.get_items_due()
        return jsonify({
            'success': True,
            'data': items,
            'count': len(items)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/reviews', methods=['POST'])
def record_review():
    """Record a review session"""
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
        return jsonify({'success': False, 'error': 'quality must be between 0 and 5'}), 400

    try:
        tracker.record_review(item_id=item_id, quality_rating=quality)
        return jsonify({'success': True, 'message': 'Review recorded successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get learning statistics"""
    try:
        stats = tracker.get_learning_stats()
        today = tracker.get_learning_today()
        
        return jsonify({
            'success': True,
            'data': {
                'stats': stats,
                'today': today
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/intent/recent', methods=['GET'])
def get_recent_intent():
    """Get the most recent intent prediction"""
    from tracker_app.db.models import SessionLocal, IntentPrediction
    try:
        with SessionLocal() as db:
            row = db.query(IntentPrediction).order_by(IntentPrediction.timestamp.desc()).first()
            if not row:
                return jsonify({'success': True, 'data': None})
            return jsonify({'success': True, 'data': {
                'id': row.id,
                'timestamp': row.timestamp,
                'predicted_intent': row.predicted_intent,
                'confidence': row.confidence,
                'user_feedback': row.user_feedback
            }})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/intent/feedback', methods=['POST'])
def send_intent_feedback():
    """Record user feedback for a prediction (for future ML training)"""
    data = request.get_json(silent=True)
    if not data or 'prediction_id' not in data or 'is_correct' not in data:
        return jsonify({'success': False, 'error': 'prediction_id and is_correct are required'}), 400
    
    try:
        validator = IntentValidator()
        validator.log_feedback(
            prediction_id=int(data['prediction_id']),
            correct=bool(data['is_correct'])
        )
        
        # If user says the prediction is incorrect, and provides the "actual_intent", we should ideally save it.
        if 'actual_intent' in data:
            from tracker_app.db.models import SessionLocal, IntentPrediction
            with SessionLocal() as db:
                pred = db.query(IntentPrediction).filter(IntentPrediction.id == int(data['prediction_id'])).first()
                if pred:
                    pred.actual_intent = str(data['actual_intent'])
                    db.commit()

        return jsonify({'success': True, 'message': 'Feedback recorded'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint for monitoring"""
    try:
        # Check DB accessibility via raw tracker status
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'components': {
                'database': 'reachable',
                'api': 'online'
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503
