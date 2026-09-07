"""Content-aware intent bias: compute_content_relevance + predict_intent override.

The classifier (6-feature vector) had no way to know WHAT is on screen, so
content-dense screens that did not match the user's study topics (file
explorer, Kaggle home, careers page) were labelled studying. These tests pin
the rule-level relevance bias built on top of the classifier output without
changing the persisted feature vector (FKT contract).
"""

import numpy as np
import pytest

from tracker_app.tracking import intent_module


class _FakeModel:
    def __init__(self, label: str):
        self.label = label

    def predict(self, X):
        return np.array([self.label] * len(X))

    def predict_proba(self, X):
        proba = np.zeros((len(X), 3))
        idx = ["idle", "passive", "studying"].index(self.label)
        proba[:, idx] = 0.9
        return proba


def _model_with(label: str, monkeypatch) -> None:
    monkeypatch.setattr(intent_module, "_load_model", lambda: {"model": _FakeModel(label)})


# ---------------------------------------------------------------------------
# compute_content_relevance
# ---------------------------------------------------------------------------


def test_relevance_full_match():
    kw = {"dynamic programming": 0.7, "array": 0.5}
    concepts = ["dynamic programming", "array", "sorting"]
    assert intent_module.compute_content_relevance(kw, concepts) == pytest.approx(1.0)


def test_relevance_partial_match_weighted():
    # 0.7 matches, 0.9 does not -> relevance = 0.7 / (0.7 + 0.9)
    kw = {"dynamic programming": 0.7, "randomize systems": 0.9}
    concepts = ["dynamic programming"]
    assert intent_module.compute_content_relevance(kw, concepts) == pytest.approx(0.7 / 1.6)


def test_relevance_nested_score_dicts():
    kw = {"dynamic programming": {"score": 0.7}, "xq": {"score": 0.9}}
    concepts = ["dynamic programming"]
    assert intent_module.compute_content_relevance(kw, concepts) == pytest.approx(0.7 / 1.6)


def test_relevance_no_match_zero():
    assert intent_module.compute_content_relevance({"kaggle home": 0.7}, ["leetcode"]) == 0.0


def test_relevance_empty_concepts_zero():
    assert intent_module.compute_content_relevance({"leetcode": 0.7}, []) == 0.0


def test_relevance_empty_keywords_zero():
    assert intent_module.compute_content_relevance({}, ["leetcode"]) == 0.0


def test_relevance_substring_token_match():
    # "longest common prefix" shares the token 'prefix' with the concept.
    kw = {"longest common prefix": 1.0}
    concepts = ["common prefix algorithms"]
    assert intent_module.compute_content_relevance(kw, concepts) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# predict_intent bias
# ---------------------------------------------------------------------------


def test_high_relevance_promotes_passive_to_studying(monkeypatch):
    _model_with("passive", monkeypatch)
    kw = {"dynamic programming": 0.7, "array": 0.5, "sorting": 0.6}
    r = intent_module.predict_intent(
        kw,
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.2,
        audio_confidence=0.9,
        known_concepts=["dynamic programming", "array", "sorting"],
    )
    assert r["intent_label"] == "studying"
    assert r["source"] == "rules+content"
    assert r["content_relevance"] == pytest.approx(1.0)


def test_low_relevance_demotes_studying_to_passive(monkeypatch):
    _model_with("studying", monkeypatch)
    kw = {"kaggle home": 0.6, "notebooks": 0.5, "competitions": 0.4}
    r = intent_module.predict_intent(
        kw,
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.2,
        audio_confidence=0.9,
        known_concepts=["dynamic programming", "leetcode", "lstm"],
    )
    assert r["intent_label"] == "passive"
    assert r["source"] == "rules+content"
    assert r["content_relevance"] == pytest.approx(0.0)


def test_mid_relevance_leaves_classifier_unchanged(monkeypatch):
    _model_with("passive", monkeypatch)
    kw = {"python": 0.1, "leetcode": 0.9, "ffz": 0.8, "qqq": 0.7}
    concepts = ["python"]  # 0.1 / 2.5 = 0.04 relevance (below RELEVANCE_LOW too)
    r = intent_module.predict_intent(
        kw,
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.2,
        audio_confidence=0.9,
        known_concepts=concepts,
    )
    assert r["intent_label"] == "passive"
    assert r["source"] == "classifier"


def test_high_relevance_studying_stays_studying(monkeypatch):
    _model_with("studying", monkeypatch)
    kw = {"dynamic programming": 0.7, "array": 0.5, "sorting": 0.6}
    r = intent_module.predict_intent(
        kw,
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.2,
        audio_confidence=0.9,
        known_concepts=["dynamic programming", "array", "sorting"],
    )
    assert r["intent_label"] == "studying"
    assert r["source"] == "classifier"


def test_explicit_known_concepts_avoids_graph_load(monkeypatch):
    # verify lazy graph lookup is NOT triggered when known_concepts is provided
    def boom():
        raise AssertionError("knowledge graph must not be loaded when known_concepts given")

    monkeypatch.setattr(intent_module, "_load_known_concepts", boom)
    kw = {"dynamic programming": 0.7, "array": 0.5}
    r = intent_module.predict_intent(
        kw,
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.2,
        audio_confidence=0.9,
        known_concepts=["dynamic programming"],
    )
    assert r["content_relevance"] == pytest.approx(0.7 / 1.2, abs=0.001)


def test_lazy_graph_load_defaults(monkeypatch):
    _model_with("passive", monkeypatch)
    monkeypatch.setattr(intent_module, "_load_known_concepts", lambda: ["dynamic programming"])
    kw = {"dynamic programming": 0.7, "array": 0.5, "sorting": 0.6}
    r = intent_module.predict_intent(
        kw,
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.2,
        audio_confidence=0.9,
    )
    assert r["intent_label"] == "studying"
    assert r["source"] == "rules+content"
