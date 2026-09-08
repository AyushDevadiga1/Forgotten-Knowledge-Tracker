"""Focused-tab intent signal against the real golden screenshots.

014 (Google Careers) is the headline regression: OCR reads a dense, career-page
screen and the classifier says studying, but the focused tab "Google Careers" is
not a study topic, so the tab gate must demote it to passive. 012 (Kaggle home)
is a documented limit: the tab itself IS study-relevant (tab_relevance 1.0), so
the tab cannot overrule the true intent - the sample demonstrates the signal is
captured, not that the threshold is wrong.

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
def test_golden_012_kaggle_tab_signal_captured():
    # Documented limit: the Kaggle-home tab genuinely matches the kaggle study
    # concept (tab_relevance 1.0), so the gate cannot overrule the idle label.
    pairs = golden_eval._load_pairs()
    concepts = golden_eval._study_concepts(pairs)
    png, label = _labelled_png("012")
    report = golden_eval._run_screenshot(png, label, known_concepts=concepts)

    intent = report["intent"]
    assert intent["predicted"] == "studying", "012 stays studying: documented hub-page limit"
    assert intent["tab_relevance"] == 1.0, "the tab signal itself must be captured"
    assert intent["source"] in ("classifier", "rules+tabs")
    assert intent["focused_tab_title"] == label.get("focused_tab_title")
    assert intent["focused_tab_url"] == label.get("focused_tab_url")
