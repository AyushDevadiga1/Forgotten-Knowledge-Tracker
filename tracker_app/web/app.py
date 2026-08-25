"""
Simple Web Dashboard for Learning Tracker

Lightweight dashboard using Flask for viewing progress and managing items
"""

from flask import Flask, send_from_directory
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from tracker_app.constants import DEFAULT_PORT
from tracker_app.config import setup_directories

setup_directories()  # Ensure data/ and models/ dirs exist before app starts

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

from tracker_app.db.db_module import init_all_databases

init_all_databases()  # Ensure tables exist for the web app


# Point static folder to the built Vite frontend
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
app = Flask(__name__, static_folder=frontend_dist)
app.logger = logging.getLogger("Dashboard")

_secret = os.getenv("SECRET_KEY")
if not _secret:
    if os.getenv("DEBUG", "false").lower() == "true":
        _secret = "dev-secret-key-change-in-production"
        app.logger.warning("Using insecure development SECRET_KEY - set SECRET_KEY in .env")
    else:
        raise RuntimeError("SECRET_KEY must be set in production (set DEBUG=true or provide SECRET_KEY in .env)")
app.config["SECRET_KEY"] = _secret
app.config["WTF_CSRF_ENABLED"] = True
app.config["WTF_CSRF_TIME_LIMIT"] = None  # No time limit for CSRF tokens

# Initialize CSRF protection
csrf = CSRFProtect(app)

# F-1: global rate limiting (flask-limiter). Defaults to ON; set
# RATELIMIT_ENABLED=false to disable. Tests keep the limiter attached but
# exempt while Flask is in TESTING mode, so the harness is never throttled.
app.config["RATELIMIT_ENABLED"] = os.getenv("RATELIMIT_ENABLED", "true").lower() == "true"
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    get_remote_address,
    default_limits=["60 per minute"],
    default_limits_exempt_when=lambda: bool(app.config.get("TESTING", False)),
)
limiter.init_app(app)

# Register API blueprints (each owns url_prefix="/api/v1"; exempt from CSRF)
from tracker_app.web.routes import ALL_BLUEPRINTS
from tracker_app.web.auth import apply_auth_to_blueprint

for bp in ALL_BLUEPRINTS:
    if bp.name != "health":
        # API key check (disabled in dev by default). The health blueprint is
        # deliberately excluded so the health probe stays unauthenticated.
        apply_auth_to_blueprint(bp)
    csrf.exempt(bp)
    app.register_blueprint(bp)

# Allow only local origins (any localhost/loopback port, e.g. the Vite dev
# server on 5173) to reach the API from JavaScript in a browser.
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:*",
                "http://127.0.0.1:*",
            ]
        }
    },
)

# Initialize Socket.IO for real-time updates
from tracker_app.web.realtime import init_socketio

socketio = init_socketio(app)

# LearningTracker singleton is managed in web/shared.py get_tracker()


# Routes
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Serve the built React frontend"""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")


def run_dashboard(debug=None, port=DEFAULT_PORT):
    """Run the Flask dashboard with Socket.IO support"""
    # Use environment variable if debug not explicitly set
    if debug is None:
        debug = os.getenv("DEBUG", "False").lower() == "true"

    app.logger.info(f"Dashboard running at: http://localhost:{port}")
    app.logger.info(f"   Add items: http://localhost:{port}/add")
    app.logger.info(f"   Stats API: http://localhost:{port}/stats")
    app.logger.info("Real-time updates: Socket.IO enabled")

    # Use socketio.run instead of app.run for WebSocket support
    host = "0.0.0.0" if os.getenv("DOCKER_CONTAINER") else "127.0.0.1"
    socketio.run(app, debug=debug, port=port, host=host, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    # In development, you can override with debug=True
    # In production, set DEBUG=False in .env
    run_dashboard()
