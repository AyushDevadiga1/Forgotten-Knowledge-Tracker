"""Socket.IO realtime layer: connects dashboard clients and broadcasts micro-quiz events."""

from flask_socketio import SocketIO, emit
from flask import request
import logging

logger   = logging.getLogger("Realtime")
socketio = None

# ── Singletons ────────────────────────────────────────────────────────────────
_tracker = None

def _get_tracker():
    global _tracker
    if _tracker is None:
        from tracker_app.learning.learning_tracker import LearningTracker
        _tracker = LearningTracker()
    return _tracker


def init_socketio(app):
    global socketio
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    @socketio.on("connect")
    def handle_connect():
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
