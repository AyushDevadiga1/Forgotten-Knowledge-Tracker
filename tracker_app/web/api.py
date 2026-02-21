"""
API Blueprint for Learning Items

RESTful API endpoints for managing learning items and reviews.
"""

import sqlite3
from flask import Blueprint, request, jsonify
from tracker_app.core.learning_tracker import LearningTracker

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
        with sqlite3.connect(tracker.db_path, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if status == 'all':
                cursor.execute("""
                    SELECT id, question, answer, difficulty, item_type, tags,
                           interval, ease_factor, repetitions, next_review_date,
                           total_reviews, correct_count, success_rate, status
                    FROM learning_items
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT id, question, answer, difficulty, item_type, tags,
                           interval, ease_factor, repetitions, next_review_date,
                           total_reviews, correct_count, success_rate, status
                    FROM learning_items
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (status, limit))

            rows = cursor.fetchall()
            items = [dict(row) for row in rows]

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
        item_id = tracker.add_learning_item(
            question=question,
            answer=answer,
            difficulty=difficulty,
            item_type=data.get('item_type', 'concept'),
            tags=data.get('tags', [])
        )
        return jsonify({'success': True, 'data': {'id': item_id}}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to create item'}), 500

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
