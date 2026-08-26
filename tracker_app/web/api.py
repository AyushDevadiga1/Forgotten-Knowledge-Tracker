"""Backward-compatibility facade for the pre-split monolithic API module.

Route implementations now live in ``tracker_app.web.routes.*`` and shared
infrastructure in ``tracker_app.web.shared``. This module only re-exports
the names other code (realtime.py, tests) still imports from here.
"""

from tracker_app.learning.learning_tracker import LearningTracker
from tracker_app.web.routes.intent import FeedbackService
from tracker_app.web.shared import (
    _parse_bool_flag,
    _retrain_lock,
    _sanitize_title,
    check_api_key,
    get_tracker,
)

__all__ = [
    "FeedbackService",
    "LearningTracker",
    "_parse_bool_flag",
    "_retrain_lock",
    "_sanitize_title",
    "check_api_key",
    "get_tracker",
]
