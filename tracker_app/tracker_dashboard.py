"""
Tracker Dashboard - Control and monitor tracking sessions from a web interface

Features:
- Start/stop tracking sessions
- Real-time session statistics
- View due concepts for review
- Analytics and insights
- Data export
"""

from flask import Flask, render_template, jsonify, request
import json
import threading
from datetime import datetime
from threading import Event
import traceback

from core.tracker_enhanced import (
    EnhancedActivityTracker,
    enhanced_track_loop,
    tracker_instance
)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['JSON_SORT_KEYS'] = False

# Tracking control
tracking_thread = None
stop_event = None
tracking_lock = threading.Lock()


@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('tracker_dashboard_new.html')


@app.route('/api/status')
def get_status():
    """Get current tracking status"""
    try:
        stats = tracker_instance.get_session_stats()
        return jsonify({
            'is_tracking': stats.get('is_active', False),
            'session_stats': stats,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'is_tracking': False
        }), 200


@app.route('/api/start-tracking', methods=['POST'])
def start_tracking():
    """Start a tracking session"""
    global tracking_thread, stop_event
    
    with tracking_lock:
        if tracker_instance.is_running:
            return jsonify({'status': 'already_running', 'message': 'Tracking already active'})
        
        try:
            # Stop previous thread if exists
            if tracking_thread and tracking_thread.is_alive():
                stop_event.set()
                tracking_thread.join(timeout=5)
            
            # Start new tracking
            stop_event = Event()
            tracker_instance.start_session()
            
            tracking_thread = threading.Thread(
                target=enhanced_track_loop,
                args=(stop_event, True),
                daemon=True
            )
            tracking_thread.start()
            
            return jsonify({
                'status': 'started',
                'timestamp': datetime.now().isoformat(),
                'message': 'Tracking started successfully'
            }), 200
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }), 500


@app.route('/api/stop-tracking', methods=['POST'])
def stop_tracking():
    """Stop the current tracking session"""
    global stop_event, tracking_thread
    
    with tracking_lock:
        if not tracker_instance.is_running:
            return jsonify({'status': 'not_running', 'message': 'No active tracking session'})
        
        try:
            if stop_event:
                stop_event.set()
            
            if tracking_thread and tracking_thread.is_alive():
                tracking_thread.join(timeout=5)
            
            tracker_instance.end_session()
            
            return jsonify({
                'status': 'stopped',
                'session_stats': tracker_instance.get_session_stats(),
                'timestamp': datetime.now().isoformat(),
                'message': 'Tracking stopped and saved'
            }), 200
        
        except Exception as e:
            traceback.print_exc()
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500


@app.route('/api/session-stats')
def get_session_stats():
    """Get current session statistics"""
    stats = tracker_instance.get_session_stats()
    return jsonify(stats)


@app.route('/api/concept-recommendations')
def get_recommendations():
    """Get top concepts to review"""
    concepts = tracker_instance.get_concept_recommendations(limit=10)
    return jsonify({
        'due_concepts': concepts,
        'count': len(concepts)
    })


@app.route('/api/intent-accuracy')
def get_intent_accuracy():
    """Get intent prediction accuracy stats"""
    stats = tracker_instance.validator.get_accuracy_stats()
    return jsonify(stats)


@app.route('/api/daily-summary')
def get_daily_summary():
    """Get daily tracking summary"""
    summary = tracker_instance.analytics.get_daily_summary()
    return jsonify(summary)


@app.route('/api/trends')
def get_trends():
    """Get trend analysis (last 7 days)"""
    trends = tracker_instance.analytics.get_trend_analysis(days=7)
    return jsonify(trends)


@app.route('/api/export-data')
def export_data():
    """Export all tracking data"""
    data = tracker_instance.export_tracking_data()
    return jsonify(data)


@app.route('/api/concept/<concept_name>')
def get_concept_history(concept_name):
    """Get history for a specific concept"""
    history = tracker_instance.scheduler.get_concept_history(concept_name, days=30)
    return jsonify({
        'concept': concept_name,
        'history': history,
        'encounter_count': len(history)
    })


if __name__ == '__main__':
    app.run(debug=True, port=5001, threaded=True)
