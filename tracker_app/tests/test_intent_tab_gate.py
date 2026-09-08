"""Focused-tab intent gate: compute_tab_relevance + predict_intent tab override.

The classifier only saw OCR + audio + attention signals; a distraction tab
(Google Careers, YouTube) or a browser chrome view (Kaggle home) was still
labelled studying because the screen text is dense and content-heavy. The
focused browser tab is treated as ground truth and OVERRIDES the OCR-only bias:
a non-study tab demotes studying->passive even when OCR looks study-relevant; a
study tab promotes passive/idle->studying. No tab keeps the OCR-only bias.

compute_tab_relevance uses concept-COVERAGE matching (full token set for
single-word concepts, >= 2 tokens otherwise) because single-token co-occurrence
made both 012-kaggle-home and 014-google-careers score 1.0 against the study
concepts contributed by the leetcode screenshots' "google cloud" etc.
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
# compute_tab_relevance (concept-coverage matcher)
# ---------------------------------------------------------------------------


def test_tab_relevance_careers_does_not_match_google_cloud():
    # The single shared token 'google' must NOT count: "careers.google.com" is
    # not the "google cloud" concept. This is the 014 regression.
    phrases = {
        "Student Researcher, PhD, Fall 2026 - Google Careers": 1.0,
        "https://careers.google.com/jobs/results/?emp_type=DEGREE": 1.0,
    }
    concepts = ["google cloud", "dynamic programming", "leetcode"]
    assert intent_module.compute_tab_relevance(phrases, concepts) == 0.0


def test_tab_relevance_kaggle_home_matches_kaggle():
    phrases = {"Kaggle: Your Machine Learning and Data Science Community": 1.0,
               "https://www.kaggle.com/": 1.0}
    assert intent_module.compute_tab_relevance(phrases, ["kaggle", "datasets"]) == 1.0


def test_tab_relevance_leetcode_problem_matches():
    phrases = {"Two Sum - LeetCode": 1.0,
               "https://leetcode.com/problems/two-sum/": 1.0}
    assert intent_module.compute_tab_relevance(phrases, ["leetcode"]) == 1.0


def test_tab_relevance_partial_tokens_do_not_cover_long_concept():
    # 'google search' shares only one token with 'google cloud' -> no cover.
    assert intent_module.compute_tab_relevance({"google search console": 1.0},
                                               ["google cloud"]) == 0.0
    # Both tokens of the concept present -> covered.
    assert intent_module.compute_tab_relevance({"google cloud platform docs": 1.0},
                                               ["google cloud"]) == 1.0


def test_tab_relevance_empty_inputs_zero():
    assert intent_module.compute_tab_relevance({}, ["leetcode"]) == 0.0
    assert intent_module.compute_tab_relevance({"Two Sum - LeetCode": 1.0}, []) == 0.0


# ---------------------------------------------------------------------------
# predict_intent tab override
# ---------------------------------------------------------------------------


def test_low_tab_demotes_studying_even_with_study_ocr(monkeypatch):
    # KEY regression: OCR screams "dynamic programming / array / sorting" but
    # the focused tab is Google Careers. The tab must win.
    _model_with("studying", monkeypatch)
    ocr = {"dynamic programming": 0.7, "array": 0.5, "sorting": 0.6}
    r = intent_module.predict_intent(
        ocr,
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.2,
        audio_confidence=0.9,
        known_concepts=["google cloud", "dynamic programming", "array", "sorting", "leetcode"],
        active_tab_title="Student Researcher, PhD, Fall 2026 - Google Careers",
        active_tab_url="https://careers.google.com/jobs/results/?emp_type=DEGREE",
    )
    assert r["intent_label"] == "passive"
    assert r["source"] == "rules+tabs"
    assert r["tab_relevance"] == 0.0
    assert r["content_relevance"] > 0.0, "demotion must come from the tab, not OCR"


def test_study_tab_promotes_passive_to_studying(monkeypatch):
    _model_with("passive", monkeypatch)
    r = intent_module.predict_intent(
        {"youtube": 0.3},
        audio_label="music",
        attention_score=45.0,
        interaction_rate=2.0,
        audio_confidence=0.8,
        known_concepts=["leetcode", "dynamic programming"],
        active_tab_title="Two Sum - LeetCode",
        active_tab_url="https://leetcode.com/problems/two-sum/",
    )
    assert r["intent_label"] == "studying"
    assert r["source"] == "rules+tabs"
    assert r["tab_relevance"] == 1.0


def test_study_tab_promotes_idle_to_studying(monkeypatch):
    _model_with("idle", monkeypatch)
    r = intent_module.predict_intent(
        {},
        audio_label="silence",
        attention_score=18.0,
        interaction_rate=0.2,
        audio_confidence=0.95,
        known_concepts=["leetcode"],
        active_tab_title="Two Sum - LeetCode",
        active_tab_url="https://leetcode.com/problems/two-sum/",
    )
    assert r["intent_label"] == "studying"
    assert r["source"] == "rules+tabs"


def test_high_tab_studying_stays_studying(monkeypatch):
    _model_with("studying", monkeypatch)
    r = intent_module.predict_intent(
        {"dynamic programming": 0.7},
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.2,
        audio_confidence=0.9,
        known_concepts=["leetcode"],
        active_tab_title="Two Sum - LeetCode",
        active_tab_url="https://leetcode.com/problems/two-sum/",
    )
    assert r["intent_label"] == "studying"
    assert r["source"] == "classifier"
    assert r["tab_relevance"] == 1.0


def test_url_only_tab_gate_engages(monkeypatch):
    _model_with("passive", monkeypatch)
    r = intent_module.predict_intent(
        {},
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.2,
        audio_confidence=0.9,
        known_concepts=["leetcode"],
        active_tab_url="https://leetcode.com/problems/contains-duplicate/",
    )
    assert r["intent_label"] == "studying"
    assert r["source"] == "rules+tabs"


def test_no_tab_keeps_ocr_only_bias_and_none_relevance(monkeypatch):
    _model_with("studying", monkeypatch)
    r = intent_module.predict_intent(
        {"kaggle home": 0.6, "notebooks": 0.5, "competitions": 0.4},
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.2,
        audio_confidence=0.9,
        known_concepts=["dynamic programming", "leetcode", "lstm"],
    )
    assert r["intent_label"] == "passive"
    assert r["source"] == "rules+content"
    assert r["tab_relevance"] is None


def test_whitespace_tab_is_no_tab(monkeypatch):
    _model_with("studying", monkeypatch)
    r = intent_module.predict_intent(
        {"dynamic programming": 0.7, "array": 0.5, "sorting": 0.6},
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.2,
        audio_confidence=0.9,
        known_concepts=["dynamic programming", "array", "sorting"],
        active_tab_title="   ",
    )
    assert r["tab_relevance"] is None
    assert r["source"] in ("classifier", "rules+content")


def test_mid_tab_relevance_leaves_classifier_unchanged(monkeypatch):
    _model_with("passive", monkeypatch)
    monkeypatch.setattr(intent_module, "compute_tab_relevance", lambda *a: 0.2)
    r = intent_module.predict_intent(
        {"something": 0.5},
        audio_label="silence",
        attention_score=50.0,
        interaction_rate=0.2,
        audio_confidence=0.9,
        known_concepts=["leetcode"],
        active_tab_title="Ambiguous Tab",
    )
    assert r["intent_label"] == "passive"
    assert r["source"] == "classifier"
    assert r["tab_relevance"] == 0.2
