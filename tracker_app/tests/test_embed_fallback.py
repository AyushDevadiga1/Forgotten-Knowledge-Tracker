"""Tests: failed lazy-model loads are not retried.

_get_embed_model and _get_spacy_vectors (knowledge_graph) and _get_nlp
(keyword_extractor) used to leave their cache at None after a failed load, so
every call re-attempted the import (possibly triggering a network download)
and logged an identical warning. Sentinels now distinguish "never tried" from
"tried and failed": a failed load logs once and returns None forever after.
"""

import sys

import pytest

from tracker_app.tracking import knowledge_graph as kg
from tracker_app.tracking import keyword_extractor as ke


@pytest.fixture(autouse=True)
def _reset_state():
    kg._embed_model = None
    kg._nlp = None
    ke._spacy_nlp = None
    yield
    kg._embed_model = None
    kg._nlp = None
    ke._spacy_nlp = None


def test_embed_load_failure_is_not_retried(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    warnings = []
    monkeypatch.setattr(kg.logger, "warning", lambda msg, *a, **k: warnings.append(str(msg)))

    assert kg._get_embed_model() is None
    assert kg._get_embed_model() is None
    assert len(warnings) == 1  # logged once, not once per call
    assert kg._embed_model is kg._EMBED_FAILED


def test_spacy_fallback_failure_is_not_retried(monkeypatch):
    monkeypatch.setitem(sys.modules, "spacy", None)
    warnings = []
    monkeypatch.setattr(kg.logger, "warning", lambda msg, *a, **k: warnings.append(str(msg)))

    assert kg._get_spacy_vectors(["alpha"]) is None
    assert kg._get_spacy_vectors(["beta"]) is None
    assert len(warnings) == 1
    assert kg._nlp is kg._SPACY_FAILED


def test_keyword_extractor_nlp_failure_is_not_retried(monkeypatch):
    monkeypatch.setitem(sys.modules, "spacy", None)
    warnings = []
    monkeypatch.setattr(ke.logger, "warning", lambda msg, *a, **k: warnings.append(str(msg)))

    assert ke._get_nlp() is None
    assert ke._get_nlp() is None
    assert len(warnings) == 1
    assert ke._spacy_nlp is ke._SPACY_NLP_FAILED
