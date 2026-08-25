"""Route modules for the Flask API.

Each module owns one Blueprint (all with url_prefix="/api/v1"); app.py
registers every entry of ALL_BLUEPRINTS.
"""

from tracker_app.web.routes.graph import graph_bp
from tracker_app.web.routes.health import health_bp
from tracker_app.web.routes.ingest import ingest_bp
from tracker_app.web.routes.intent import intent_bp
from tracker_app.web.routes.items import items_bp
from tracker_app.web.routes.quiz import quiz_bp
from tracker_app.web.routes.session import session_bp
from tracker_app.web.routes.stats import stats_bp

ALL_BLUEPRINTS = (
    health_bp,
    items_bp,
    quiz_bp,
    stats_bp,
    graph_bp,
    session_bp,
    intent_bp,
    ingest_bp,
)

__all__ = [
    "ALL_BLUEPRINTS",
    "graph_bp",
    "health_bp",
    "ingest_bp",
    "intent_bp",
    "items_bp",
    "quiz_bp",
    "session_bp",
    "stats_bp",
]
