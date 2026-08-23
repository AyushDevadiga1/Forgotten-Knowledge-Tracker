"""Shared utility functions for the FKT codebase."""

import datetime as _stdlib_dt


def utcnow():
    """Timezone-aware UTC now without tzinfo (Python 3.12+ deprecation safe).

    Returns a naive datetime in UTC, compatible with the ORM's
    DateTime columns which store naive timestamps.
    """
    return _stdlib_dt.datetime.now(_stdlib_dt.timezone.utc).replace(tzinfo=None)
