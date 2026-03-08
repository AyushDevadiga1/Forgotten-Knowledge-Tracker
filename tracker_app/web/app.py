"""
Simple Web Dashboard for Learning Tracker

Lightweight dashboard using Flask for viewing progress and managing items
"""

from flask import Flask, send_from_directory, request, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from tracker_app.core.learning_tracker import LearningTracker
import os
import logging
from contextlib import closing
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from tracker_app.config import DATA_DIR, setup_directories
setup_directories()  # Ensure data/ and models/ dirs exist before app starts

# Point static folder to the built Vite frontend
frontend_dist = os.path.join(os.path.dirname(__file__), 'frontend', 'dist')
app = Flask(__name__, static_folder=frontend_dist)
app.logger = logging.getLogger("Dashboard")

# Security Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None  # No time limit for CSRF tokens

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Register API blueprint (exempt from CSRF for API endpoints)
from tracker_app.web.api import api_bp
from tracker_app.web.auth import apply_auth_to_blueprint
apply_auth_to_blueprint(api_bp)   # API key check (disabled in dev by default)
csrf.exempt(api_bp)
app.register_blueprint(api_bp)

# Allow Vite dev server (localhost:5173) to reach the API
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}})

# Initialize Socket.IO for real-time updates
from tracker_app.web.realtime import init_socketio
socketio = init_socketio(app)

tracker = LearningTracker()

# Routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve the built React frontend"""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


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
