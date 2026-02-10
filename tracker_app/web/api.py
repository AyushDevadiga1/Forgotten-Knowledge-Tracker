"""
API Blueprint for Learning Items

RESTful API endpoints for managing learning items and reviews.
"""

from flask import Blueprint, request, jsonify
from tracker_app.core.learning_tracker import LearningTracker

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
tracker = LearningTracker()

@api_bp.route('/items', methods=['GET'])
def get_items():
    """Get all learning items"""
    try:
        # Get query parameters
        status = request.args.get('status', 'active')
        limit = int(request.args.get('limit', 50))
        
        # TODO: Implement filtering in LearningTracker
        items = []  # Placeholder
        
        return jsonify({
            'success': True,
            'data': items,
            'count': len(items)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/items', methods=['POST'])
def create_item():
    """Create a new learning item"""
    try:
        data = request.get_json()
        
        item_id = tracker.add_learning_item(
            question=data.get('question'),
            answer=data.get('answer'),
            difficulty=data.get('difficulty', 'medium'),
            item_type=data.get('item_type', 'concept'),
            tags=data.get('tags', [])
        )
        
        return jsonify({
            'success': True,
            'data': {'id': item_id}
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

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
    try:
        data = request.get_json()
        
        tracker.record_review(
            item_id=data.get('item_id'),
            quality=int(data.get('quality', 3))
        )
        
        return jsonify({
            'success': True,
            'message': 'Review recorded successfully'
        })
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
