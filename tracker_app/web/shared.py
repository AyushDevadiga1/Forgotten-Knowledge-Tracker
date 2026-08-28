"""Shared web-layer infrastructure.

Holds the pieces every route module needs but that must exist exactly once:
the LearningTracker singleton, the background-retrain lock (C-2), the
API-key gate, and small parsing/sanitising helpers used by several modules.
"""

import os
import re
import threading

from flask import jsonify, request

from tracker_app.learning.learning_tracker import LearningTracker

# C-2: only one background retraining subprocess may run at a time - two
# concurrent writes to models/intent_classifier.pkl corrupt the pickle.
_retrain_lock = threading.Lock()

# Singleton tracker (fixes double-instantiation)
_tracker: LearningTracker | None = None


def get_tracker() -> LearningTracker:
    global _tracker
    if _tracker is None:
        _tracker = LearningTracker()
    return _tracker


def check_api_key():
    """Require API key on all endpoints except health and static."""
    if request.endpoint and request.endpoint.endswith("health_check"):
        return None
    no_auth = os.environ.get("NO_AUTH", "false").lower() == "true"
    api_key = os.environ.get("API_KEY", "")
    if no_auth or not api_key:
        return None  # auth disabled (dev mode)
    provided = request.headers.get("X-API-Key", "")
    if not provided or provided != api_key:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return None


def _parse_bool_flag(value):
    """Strictly parse a JSON boolean-ish flag.

    Accepts real JSON booleans plus the common string/number forms
    'true'/'false' (case-insensitive, '1'/'0'). Returns None for anything
    unrecognised so callers can reject it with a 400 instead of silently
    treating a value like the string "false" as True (bool("false") is True).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "1"):
            return True
        if v in ("false", "0"):
            return False
        return None
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    return None


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _sanitize_title(raw) -> str:
    """Strip C0/C1 control characters and collapse whitespace (F-2).

    Browser extensions have shipped titles containing escape sequences,
    null bytes, and newlines. Those reach ConceptEncounter.context_snippet
    and later render as raw control bytes in the UI. Printable Unicode is
    preserved; control runs and stray whitespace are removed/collapsed.
    """
    if not raw:
        return ""
    cleaned = _CONTROL_CHARS_RE.sub("", str(raw))
    return " ".join(cleaned.split())
