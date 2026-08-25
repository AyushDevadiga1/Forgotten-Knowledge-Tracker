"""Browser-extension ingestion endpoint."""

import logging

from flask import Blueprint, jsonify, request

from tracker_app.constants import (
    BROWSER_INGEST_MAX_TEXT,
    BROWSER_INGEST_MIN_TEXT,
    TITLE_MAX_LENGTH,
    CONTEXT_MAX_LENGTH,
    TEXT_TOP_KEYWORDS,
)
from tracker_app.web.shared import _sanitize_title, check_api_key

logger = logging.getLogger("API")

ingest_bp = Blueprint("ingest", __name__, url_prefix="/api/v1")
ingest_bp.before_request(check_api_key)


@ingest_bp.route("/ingest", methods=["POST"])
def browser_ingest():
    """
    Receive text from the browser extension.
    Runs YAKE! keyword extraction + concept scheduling.
    Primary OCR alternative for web-based study sessions.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Request body must be valid JSON"}), 400
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400
    if "text" not in data:
        return jsonify({"success": False, "error": "text field required"}), 400

    text = str(data.get("text", ""))[:BROWSER_INGEST_MAX_TEXT]
    text_truncated = len(str(data.get("text", ""))) > BROWSER_INGEST_MAX_TEXT
    title = _sanitize_title(data.get("title", ""))[:TITLE_MAX_LENGTH]

    if len(text.strip()) < BROWSER_INGEST_MIN_TEXT:
        return jsonify({"success": True, "message": "Text too short Ã¢â‚¬â€ skipped"})

    try:
        from tracker_app.tracking.privacy_filter import (
            sanitize_text_for_storage,
            is_sensitive_window,
            strip_redaction_markers,
            filter_sensitive_keywords,
        )
        from tracker_app.tracking.keyword_extractor import extract_concepts
        from tracker_app.learning.concept_scheduler import ConceptScheduler
        from tracker_app.learning.text_quality_validator import validate_and_clean_extraction

        # Sensitive window title -> drop it (never stored as context).
        if is_sensitive_window(title):
            title = ""

        # Privacy gate FIRST - the extension path previously bypassed the
        # redactor entirely, so emails/passwords/SSNs reached add_concept.
        sanitized = sanitize_text_for_storage(text)
        if not sanitized["safe_to_store"]:
            return jsonify({"success": True, "message": "Text filtered as sensitive"})

        text = strip_redaction_markers(sanitized["text"])

        validation = validate_and_clean_extraction(text)
        if not validation.get("is_useful", False):
            return jsonify({"success": True, "message": "Text filtered as low quality"})

        keywords = filter_sensitive_keywords(extract_concepts(validation["cleaned_text"], top_n=TEXT_TOP_KEYWORDS))

        if not keywords:
            return jsonify({"success": True, "message": "No keywords extracted"})

        scheduler = ConceptScheduler()
        saved = 0
        for concept, score in keywords.items():
            if len(concept) >= 3:
                result = scheduler.add_concept(
                    concept=concept,
                    confidence=float(score),
                    context=f"browser:{title[:CONTEXT_MAX_LENGTH]}",
                    attention_at_encoding=60.0,  # assume moderate engagement
                    source="browser_extension",
                )
                if result:
                    saved += 1

        return jsonify(
            {
                "success": True,
                "concepts_saved": saved,
                "keywords": list(keywords.keys())[:5],
                "text_truncated": text_truncated,
            }
        )
    except Exception as e:
        logger.error(f"browser_ingest: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
