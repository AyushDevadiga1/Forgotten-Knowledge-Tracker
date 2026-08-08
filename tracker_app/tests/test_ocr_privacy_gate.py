"""
Tests for the mandatory privacy gate in the OCR pipeline (Phase 12, [C-1]/[M-5]).

C-1: privacy filtering must be a hard, module-level import — never a best-effort
     import that silently disappears. A capture with sensitive content must be
     redacted before it ever reaches keyword/concept extraction.
M-5: `should_skip_window()` must delegate to the canonical keyword list in
     `privacy_filter.py`, so the OCR module and the privacy module can never
     disagree about which window titles are sensitive.

Skipped in CI: `ocr_module` needs cv2/mss/pytesseract, which the reduced Linux
test set does not install. Locally (full dev env) these run.
"""

import networkx as nx
import pytest

pytest.importorskip("cv2")
pytest.importorskip("mss")

from tracker_app.tracking import ocr_module
from tracker_app.tracking import privacy_filter

# Union of the two lists that previously existed independently (privacy_filter
# grew these after ocr_module's local copy was written). Every one must be
# treated as sensitive by the single canonical implementation.
SENSITIVE_TITLES = [
    "Password Manager - Vault",
    "Gmail - Sign in",
    "Company SSO Login",
    "Authentication required",
    "Online Banking - Chase",
    "PayPal - Checkout",
    "Credit Card Details",
    "Secure Payment Gateway",
    "Private browsing",
    "Incognito window",
    "InPrivate window",
    "Medical records portal",
    "Health insurance claims",
    "Prescription refill",
]


def test_should_skip_window_delegates_to_privacy_filter():
    for title in SENSITIVE_TITLES:
        assert ocr_module.should_skip_window(title) == privacy_filter.is_sensitive_window(title), title


def test_should_skip_window_catches_extended_keyword_union():
    # Regression: 'authentication', 'payment', 'health', 'prescription' existed
    # only in privacy_filter's list. After M-5 both lists agree — all must skip.
    for title in SENSITIVE_TITLES:
        assert ocr_module.should_skip_window(title) is True, title


def test_should_skip_window_accepts_study_titles():
    assert ocr_module.should_skip_window("Python Documentation - Functions") is False
    assert ocr_module.should_skip_window("") is False
    assert ocr_module.should_skip_window(None) is False


def test_privacy_gate_is_mandatory_module_level_import():
    # C-1: sanitize_text_for_storage must be the canonical function bound at
    # import time — not a lazily-imported, swallowable dependency.
    assert ocr_module.sanitize_text_for_storage is privacy_filter.sanitize_text_for_storage


def test_extract_keywords_redacts_sensitive_content(monkeypatch):
    # Keep the pipeline hermetic: no real DB / knowledge-graph access.
    monkeypatch.setattr(ocr_module, "get_graph", lambda: nx.Graph())

    text = (
        "My credit card is 4111-1111-1111-1111 and I use it for online purchases. "
        "The vendor processes every transaction securely."
    )
    keywords = ocr_module.extract_keywords(text, top_n=10)

    raw_card = "4111-1111-1111-1111"
    assert raw_card not in keywords, "Raw credit card must never surface as a keyword"
    assert not any("[REDACTED" in kw for kw in keywords)
