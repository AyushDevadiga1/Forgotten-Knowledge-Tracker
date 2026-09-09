"""Focused-tab intent signal against the real golden screenshots.

014 (Google Careers) is the headline regression: OCR reads a dense, career-page
screen and the classifier says studying, but the focused tab "Google Careers" is
not a study topic, so the tab gate must demote it to passive. 012 (Kaggle home)
exercises the navigation-surface (hub) rule: the tab itself IS study-relevant
(tab_relevance 1.0), so the tab gate cannot and must not overrule the idle
intent - instead the post-gate hub rule (root/home/feed URL) demotes studying
to idle. The sample proves the hub rule, not the threshold.

Skipped in CI / lean environments: needs cv2 + tesseract + data/golden.
"""

import importlib.util
import pathlib
import shutil
import sys

import pytest

pytest.importorskip("cv2")
import cv2  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLDEN_DIR = ROOT / "data" / "golden"

from tracker_app.config import TESSERACT_PATH  # noqa: E402


def _tesseract_available() -> bool:
    if TESSERACT_PATH and pathlib.Path(TESSERACT_PATH).exists():
        return True
    return shutil.which("tesseract") is not None


needs_golden = pytest.mark.skipif(
    not GOLDEN_DIR.exists() or not (GOLDEN_DIR / "014-google-careers.png").exists(),
    reason="golden dataset screenshots missing",
)
needs_tesseract = pytest.mark.skipif(not _tesseract_available(), reason="tesseract unavailable")

# conftest.py stubs psutil globally for headless CI, but the real persisted
# classifier calls psutil.Process during predict(). This golden test needs the
# genuine stack (cv2 + tesseract + classifier), so restore the real psutil for
# this process; without it predict_intent falls to the rules path and the
# headline regression would not reproduce.
if not hasattr(sys.modules.get("psutil"), "Process"):
    _stub = sys.modules.pop("psutil", None)
    try:
        import psutil as _real_psutil  # fresh import (stub removed)
        sys.modules["psutil"] = _real_psutil
    except Exception:
        if _stub is not None:
            sys.modules["psutil"] = _stub

_spec = importlib.util.spec_from_file_location("golden_eval", ROOT / "tools" / "golden_eval.py")
golden_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(golden_eval)


def _labelled_png(prefix: str):
    png = next(p for p in GOLDEN_DIR.glob(f"{prefix}-*.png") if p.name.startswith(f"{prefix}-"))
    return png, golden_eval.find_label(png, prefix)


@needs_golden
@needs_tesseract
def test_golden_014_careers_demotes_on_tab():
    pairs = golden_eval._load_pairs()
    concepts = golden_eval._study_concepts(pairs)
    png, label = _labelled_png("014")
    report = golden_eval._run_screenshot(png, label, known_concepts=concepts)

    intent = report["intent"]
    assert intent["predicted"] == "passive"
    assert intent["true"] == "passive"
    assert intent["correct"] is True
    assert intent["source"] == "rules+tabs"
    assert intent["tab_relevance"] == 0.0
    assert intent["content_relevance"] > 0.0, "demotion must come from the tab, not OCR"


@needs_golden
@needs_tesseract
def test_golden_012_kaggle_hub_demoted_to_idle():
    # Kaggle home is a navigation surface (root URL). The hub rule fires after
    # the tab gate: the study-relevant tab (tab_relevance 1.0) can never win
    # because a root/home/feed portal is not study content. Harness interaction
    # (0.2) < HUB_IDLE_INTERACTION -> idle, not passive.
    pairs = golden_eval._load_pairs()
    concepts = golden_eval._study_concepts(pairs)
    png, label = _labelled_png("012")
    report = golden_eval._run_screenshot(png, label, known_concepts=concepts)

    intent = report["intent"]
    assert intent["predicted"] == "idle", "012 root hub URL must demote studying -> idle"
    assert intent["correct"] is True
    assert intent["source"] == "rules+hub"
    assert intent["tab_relevance"] == 1.0, "the tab signal itself must be captured"
    assert intent["focused_tab_title"] == label.get("focused_tab_title")
    assert intent["focused_tab_url"] == label.get("focused_tab_url")

@needs_golden
@needs_tesseract
def test_golden_014_without_tab_keeps_studying_bias():
    # Causal proof for the headline regression: the SAME screenshot, OCR and
    # concepts, run with the tab fields stripped, must land on studying. Only
    # then is the with-tab demotion attributable to the focused-tab signal and
    # not to the classifier/rules agreeing on their own.
    pairs = golden_eval._load_pairs()
    concepts = golden_eval._study_concepts(pairs)
    png, label = _labelled_png("014")

    no_tab = dict(label)
    no_tab.pop("focused_tab_title", None)
    no_tab.pop("focused_tab_url", None)
    report = golden_eval._run_screenshot(png, no_tab, known_concepts=concepts)

    intent = report["intent"]
    assert intent["predicted"] == "studying", \
        f"expected the OCR-only bias (studying) without a tab, got {intent['predicted']}"
    assert intent["tab_relevance"] is None
    assert intent["correct"] is False
