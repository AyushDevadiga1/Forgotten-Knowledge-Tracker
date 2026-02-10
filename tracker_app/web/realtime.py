"""
Real-time Updates with Socket.IO

Provides live dashboard updates for tracker status and learning progress.
"""

from flask_socketio import SocketIO, emit
from flask import request
import threading
import time

socketio = None

def init_socketio(app):
    """Initialize Socket.IO with Flask app"""
    global socketio
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        print(f"Client connected: {request.sid}")
        emit('status', {'message': 'Connected to FKT server'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f"Client disconnected: {request.sid}")
    
    @socketio.on('request_stats')
    def handle_stats_request():
        """Send current statistics to client"""
        from tracker_app.core.learning_tracker import LearningTracker
        tracker = LearningTracker()
        stats = tracker.get_learning_stats()
        emit('stats_update', stats)
    
    return socketio

def broadcast_tracker_status(status_data):
    """Broadcast tracker status to all connected clients"""
    if socketio:
        socketio.emit('tracker_status', status_data, broadcast=True)

def broadcast_concept_discovered(concept_data):
    """Broadcast newly discovered concept"""
    if socketio:
        socketio.emit('concept_discovered', concept_data, broadcast=True)

def broadcast_review_completed(review_data):
    """Broadcast completed review"""
    if socketio:
        socketio.emit('review_completed', review_data, broadcast=True)

# Background task for periodic updates
def background_stats_updater(app):
    """Send periodic stats updates to all clients"""
    with app.app_context():
        while True:
            time.sleep(30)  # Update every 30 seconds
            try:
                from tracker_app.core.learning_tracker import LearningTracker
                tracker = LearningTracker()
                stats = tracker.get_learning_stats()
                if socketio:
                    socketio.emit('stats_update', stats, broadcast=True)
            except Exception as e:
                print(f"Error in background updater: {e}")
