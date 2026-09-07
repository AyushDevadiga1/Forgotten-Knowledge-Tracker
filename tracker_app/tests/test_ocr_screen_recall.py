"""Golden-driven OCR regression tests.

The golden dataset (data/golden/) proved that extract_text() dropped every word
below Tesseract confidence 30, and real on-screen study content scores 0-9, so
studied pages collapsed to "" (concept recall 0.00 on all 15 images). This pins
the pipeline to actually preserve the expected concepts from real screenshots.

Skipped in CI / lean environments: needs cv2 + tesseract + data/golden.
"""

import pathlib
import shutil

import numpy as np
import pytest

pytest.importorskip("cv2")
import cv2  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLDEN_DIR = ROOT / "data" / "golden"

from tracker_app.config import TESSERACT_PATH  # noqa: E402
from tracker_app.tracking import ocr_module  # noqa: E402


def _tesseract_available() -> bool:
    if TESSERACT_PATH and pathlib.Path(TESSERACT_PATH).exists():
        return True
    return shutil.which("tesseract") is not None


needs_golden = pytest.mark.skipif(
    not GOLDEN_DIR.exists() or not (GOLDEN_DIR / "005-leetcode.png").exists(),
    reason="golden dataset screenshots missing",
)
needs_tesseract = pytest.mark.skipif(not _tesseract_available(), reason="tesseract unavailable")


def _extract(png_name: str) -> str:
    img = cv2.imread(str(GOLDEN_DIR / png_name))
    proc = ocr_module.preprocess_image(img)
    return ocr_module.extract_text(proc) or ""


def _concept_hits(text: str, expected: list) -> list:
    low = " ".join(text.lower().split())
    return [e for e in expected if e.lower() in low]


@needs_golden
@needs_tesseract
def test_screen_concepts_survive_ocr_054():
    # Regression: previously "005-leetcode.png" and "012-kaggle-home.png"
    # produced NO expected concept in OCR text (recall 0.00); the confidence
    # threshold discarded real page words. At least half must now survive.
    cases = [
        ("005-leetcode.png", ["leetcode", "two sum", "dynamic programming", "array", "sorting"]),
        ("012-kaggle-home.png", ["kaggle", "datasets", "notebooks", "competitions"]),
    ]
    for png, expected in cases:
        text = _extract(png)
        hits = _concept_hits(text, expected)
        assert len(hits) >= max(2, len(expected) // 2), (
            f"{png}: OCR kept only {hits} of {expected}\ntext={text[:200]!r}"
        )


@needs_golden
@needs_tesseract
def test_ocr_text_is_not_empty_on_study_screenshot():
    # Regression: many golden images reduced to 0 chars of text. The pipeline
    # must return a substantive extraction from a text-heavy study window.
    text = _extract("005-leetcode.png")
    assert len(text.strip()) > 40, f"expected substantial text, got {text[:80]!r}"


def test_preprocess_image_is_grayscale_not_binarized():
    # Regression: Otsu + morphological-close binarization destroyed modern
    # screen fonts (recall 0.80 -> 0.57). Output must stay a multi-level
    # grayscale so thin antialiased text survives.
    img = np.zeros((120, 240, 3), dtype=np.uint8)
    img[:] = (200, 200, 200)
    for i, gray in enumerate((210, 128, 105, 45)):
        cv2.rectangle(img, (i * 60, 30), (i * 60 + 30, 90), (gray, gray, gray), -1)

    proc = ocr_module.preprocess_image(img)
    assert proc is not None
    assert proc.ndim == 2, "output must be single-channel grayscale"
    assert len(np.unique(proc)) > 2, "must not collapse to a binary image"
