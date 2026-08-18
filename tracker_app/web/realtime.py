"""Socket.IO realtime layer: connects dashboard clients and broadcasts micro-quiz events."""

import hmac
import os
from flask_socketio import SocketIO, emit
from flask import request
import logging

logger   = logging.getLogger("Realtime")
socketio = None

# ── Singletons ────────────────────────────────────────────────────────────────
def _get_tracker():
    from tracker_app.web.api import get_tracker
    return get_tracker()


def _ws_auth_ok():
    """Check API key on WebSocket connections (same logic as HTTP)."""
    api_key = os.getenv("API_KEY", "")
    no_auth = os.getenv("NO_AUTH", "false").lower() == "true"
    if no_auth or not api_key:
        return True
    provided = request.args.get("api_key", "") or request.headers.get("X-API-Key", "")
    return bool(provided) and hmac.compare_digest(provided, api_key)


def init_socketio(app):
    global socketio
    # Match the Flask CORS origins — both dev (5173) and prod (5000)
    socketio = SocketIO(app, cors_allowed_origins=[
        "http://localhost:5000", "http://127.0.0.1:5000",
        "http://localhost:5173", "http://127.0.0.1:5173",
    ], async_mode="threading")

    @socketio.on("connect")
    def handle_connect():
        if not _ws_auth_ok():
            logger.warning("WebSocket connection rejected: invalid or missing API key")
            return False  # reject the connection
        logger.debug(f"Client connected: {request.sid}")
        emit("status", {"message": "Connected to FKT 2.0"})

    @socketio.on("disconnect")
    def handle_disconnect():
        logger.debug(f"Client disconnected: {request.sid}")

    @socketio.on("request_stats")
    def handle_stats_request():
        try:
            stats = _get_tracker().get_learning_stats()
            emit("stats_update", stats)
        except Exception as e:
            logger.warning(f"stats request error: {e}")

    return socketio


# ── Broadcast helpers (called from loop.py) ───────────────────────────────────

def broadcast_micro_quiz(quiz_data: dict):
    """Broadcast a micro-quiz to all connected dashboard clients."""
    if socketio:
        socketio.emit("micro_quiz", quiz_data, broadcast=True)
        logger.info(f"Micro-quiz broadcast: '{quiz_data.get('concept', '?')}'")