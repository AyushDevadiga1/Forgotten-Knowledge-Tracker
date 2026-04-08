# web/realtime.py — FKT 2.0 Phase 11
# Fixes:
#   - LearningTracker singleton (was instantiated on every Socket.IO event)
#   - Added broadcast_micro_quiz() for Phase 7 quiz interrupt
#   - background_stats_updater runs every 30s via Socket.IO

from flask_socketio import SocketIO, emit
from flask import request
import threading
import time
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


# ── Broadcast helpers (called from loop.py / quiz_engine) ─────────────────────

def broadcast_tracker_status(status_data: dict):
    if socketio:
        socketio.emit("tracker_status", status_data, broadcast=True)


def broadcast_concept_discovered(concept_data: dict):
    if socketio:
        socketio.emit("concept_discovered", concept_data, broadcast=True)


def broadcast_review_completed(review_data: dict):
    if socketio:
        socketio.emit("review_completed", review_data, broadcast=True)


def broadcast_micro_quiz(quiz_data: dict):
    """Broadcast a micro-quiz to all connected dashboard clients (Phase 7)."""
    if socketio:
        socketio.emit("micro_quiz", quiz_data, broadcast=True)
        logger.info(f"Micro-quiz broadcast: '{quiz_data.get('concept', '?')}'")


# ── Background periodic stats push ────────────────────────────────────────────

def background_stats_updater(app):
    """Push stats every 30 s to all connected clients."""
    with app.app_context():
        while True:
            time.sleep(30)
            try:
                stats = _get_tracker().get_learning_stats()
                if socketio:
                    socketio.emit("stats_update", stats, broadcast=True)
            except Exception as e:
                logger.debug(f"Background stats error: {e}")
