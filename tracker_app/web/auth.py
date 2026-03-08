"""
Simple API Key Authentication Middleware for FKT

Usage:
  Set API_KEY in .env file.
  Pass key as: X-API-Key: <key> header on all API requests (or skip for local dev with NO_AUTH=true).
"""

import os
import functools
from flask import request, jsonify

# Loaded from environment. If empty or not set, auth is disabled (dev mode).
_API_KEY = os.getenv("API_KEY", "")
_NO_AUTH = os.getenv("NO_AUTH", "true").lower() == "true"  # Default: no auth in dev


def require_api_key(f):
    """
    Decorator that enforces API key authentication.
    Skip if NO_AUTH=true or API_KEY is unset (local dev friendly).
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        # In dev mode or if no key configured, skip auth
        if _NO_AUTH or not _API_KEY:
            return f(*args, **kwargs)

        provided_key = request.headers.get("X-API-Key", "")
        if not provided_key:
            return jsonify({
                "success": False,
                "error": "Missing API key. Provide X-API-Key header."
            }), 401

        if provided_key != _API_KEY:
            return jsonify({
                "success": False,
                "error": "Invalid API key."
            }), 403

        return f(*args, **kwargs)
    return decorated


def apply_auth_to_blueprint(bp):
    """
    Apply the API key check as a before_request hook to an entire Blueprint.
    This avoids decorating each route individually.
    """
    @bp.before_request
    def check_key():
        if _NO_AUTH or not _API_KEY:
            return  # Allow all in dev
        provided_key = request.headers.get("X-API-Key", "")
        if not provided_key:
            return jsonify({"success": False, "error": "Missing X-API-Key header."}), 401
        if provided_key != _API_KEY:
            return jsonify({"success": False, "error": "Forbidden: invalid API key."}), 403
