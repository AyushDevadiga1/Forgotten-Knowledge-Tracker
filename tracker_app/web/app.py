"""
Simple Web Dashboard for Learning Tracker

Lightweight dashboard using Flask for viewing progress and managing items
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from tracker_app.core.learning_tracker import LearningTracker
from tracker_app.core.sm2_memory_model import SM2Scheduler, format_next_review
from datetime import datetime, timedelta
import sqlite3
import json
import os
import logging
from contextlib import closing
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from tracker_app.config import DATA_DIR, setup_directories
setup_directories()  # Ensure data/ and models/ dirs exist before app starts

app = Flask(__name__)
app.logger = logging.getLogger("Dashboard")

# Security Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None  # No time limit for CSRF tokens

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Register API blueprint (exempt from CSRF for API endpoints)
from tracker_app.web.api import api_bp
csrf.exempt(api_bp)
app.register_blueprint(api_bp)

# Allow Vite dev server (localhost:5173) to reach the API
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}})

# Initialize Socket.IO for real-time updates
from tracker_app.web.realtime import init_socketio
socketio = init_socketio(app)

tracker = LearningTracker()

def get_discovered_concepts(limit=5):
    """Fetch recently discovered concepts from tracker"""
    try:
        db_path = str(DATA_DIR / "tracking_concepts.db")
        if not os.path.exists(db_path):
            return []

        with closing(sqlite3.connect(db_path, timeout=5)) as conn:
            c = conn.cursor()
            c.execute('''
                SELECT concept, relevance_score, last_seen
                FROM tracked_concepts
                ORDER BY last_seen DESC
                LIMIT ?
            ''', (limit,))
            rows = c.fetchall()
        return [{'concept': r[0], 'relevance': round(r[1], 2), 'last_seen': r[2]} for r in rows]
    except Exception as e:
        app.logger.error(f"Error fetching discovered concepts: {e}")
        return []

# Routes
@app.route('/')
def index():
    """Dashboard home"""
    stats = tracker.get_learning_stats()
    due_items = tracker.get_items_due()

    # Get recent items — use context manager to ensure connection always closes
    with closing(sqlite3.connect(tracker.db_path, timeout=10)) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM learning_items WHERE status = "active" ORDER BY created_at DESC LIMIT 5')
        recent_rows = c.fetchall()

    recent_items = [tracker._row_to_dict(row) for row in recent_rows]
    discovered_concepts = get_discovered_concepts()

    return render_template(
        "index.html",
        stats=stats,
        due_items=due_items,
        recent_items=recent_items,
        discovered_concepts=discovered_concepts
    )


@app.route('/add', methods=['GET', 'POST'])
def add_item_page():
    """Add item page"""
    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        answer = request.form.get('answer', '').strip()
        difficulty = request.form.get('difficulty', 'medium')
        item_type = request.form.get('item_type', 'concept')
        tags_str = request.form.get('tags', '')
        tags = [t.strip() for t in tags_str.split(',') if t.strip()]

        if not question:
            return "Error: question is required", 400
        if not answer:
            return "Error: answer is required", 400
        if difficulty not in {'easy', 'medium', 'hard'}:
            return "Error: difficulty must be easy, medium, or hard", 400

        try:
            tracker.add_learning_item(
                question=question,
                answer=answer,
                difficulty=difficulty,
                item_type=item_type,
                tags=tags
            )
            return redirect(url_for('index'))
        except Exception as e:
            return f"Error: {e}", 400
    
    return render_template("add.html")


@app.route('/review')
def review_session():
    """Start review session"""
    items = tracker.get_items_due()
    if not items:
        # If no items due, maybe try active items that haven't been reviewed in a while?
        # For now, just show empty
        return render_template("review.html", item=None, current_index=0, total_count=0)
        
    # Redirect to first item review
    return redirect(url_for('review_item', item_id=items[0]['id']))


@app.route('/review/<item_id>', methods=['GET', 'POST'])
def review_item(item_id):
    """Review single item"""
    if request.method == 'POST':
        quality_raw = request.form.get('quality', '3')
        try:
            quality = int(quality_raw)
            if not (0 <= quality <= 5):
                return "Error: quality must be 0-5", 400
        except (ValueError, TypeError):
            return "Error: quality must be an integer", 400
        try:
            tracker.record_review(item_id, quality_rating=quality)
            # Find next due item
            items = tracker.get_items_due()
            if items:
                return redirect(url_for('review_item', item_id=items[0]['id']))
            else:
                return redirect(url_for('review_complete'))
        except Exception as e:
            return f"Error: {e}", 400
    
    item = tracker.get_item(item_id)
    items_due = tracker.get_items_due()
    # Calculate index
    ids = [i['id'] for i in items_due]
    try:
        current_index = ids.index(item_id)
    except ValueError:
        current_index = 0 # Item might have just been reviewed or out of order
        
    return render_template("review.html", item=item, current_index=current_index, total_count=len(items_due))

@app.route('/review/complete')
def review_complete():
    return render_template("review.html", item=None, current_index=0, total_count=0)


@app.route('/stats')
def stats():
    """Get statistics API"""
    stats = tracker.get_learning_stats()
    today = tracker.get_learning_today()
    return jsonify({
        'stats': stats,
        'today': today
    })


@app.route('/search')
def search():
    """Search items"""
    q = request.args.get('q', '')
    items = tracker.search_items(q)
    return jsonify([{
        'id': item['id'],
        'question': item['question'],
        'type': item['item_type'],
        'success_rate': item['success_rate'],
        'total_reviews': item['total_reviews']
    } for item in items])


def run_dashboard(debug=None, port=5000):
    """Run the Flask dashboard with Socket.IO support"""
    # Use environment variable if debug not explicitly set
    if debug is None:
        debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"\n[INFO] Dashboard running at: http://localhost:{port}")
    print(f"   Add items: http://localhost:{port}/add")
    print(f"   Stats API: http://localhost:{port}/stats")
    print(f"   Real-time updates: Socket.IO enabled\n")
    
    # Use socketio.run instead of app.run for WebSocket support
    socketio.run(app, debug=debug, port=port, host='127.0.0.1', allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    # In development, you can override with debug=True
    # In production, set DEBUG=False in .env
    run_dashboard()
