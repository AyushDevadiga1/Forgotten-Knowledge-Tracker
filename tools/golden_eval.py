"""Golden-dataset evaluation runner for FKT.

Measures the real OCR -> keyword -> intent pipeline against hand-labeled
screenshots in data/golden/, following the plan in GOLDEN_DATASET.md.

For every pair (NNN-*.png, NNN-*-label.json) it reports:
  - OCR text recall  : which expected concepts appear anywhere in OCR text
  - Keyword precision/recall : which expected concepts were surfaced as keywords
  - Hierarchy        : title/heading hits from the label vs OCR text
  - Intent           : predict_intent() under a fixed documented "reading at
                       screen" context (silence, neutral attention 50, low
                       interaction 0.2) compared with the label's true_intent

Emits:
  outputs/golden_report.json  - full per-screenshot + aggregate report

Usage:
    python tools/golden_eval.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402

from tracker_app.constants import TEXT_TOP_KEYWORDS  # noqa: E402
from tracker_app.tracking.ocr_module import (  # noqa: E402
    extract_keywords,
    extract_text,
    preprocess_image,
)
from tracker_app.tracking.keyword_extractor import get_keyword_extractor  # noqa: E402
from tracker_app.tracking.intent_module import predict_intent  # noqa: E402
from tracker_app.tracking.privacy_filter import (  # noqa: E402
    sanitize_text_for_storage,
    strip_redaction_markers,
)

GOLDEN_DIR = ROOT / "data" / "golden"
OUT_DIR = ROOT / "outputs"

# Intent context for a person reading at the screen (the scenario the user
# reported as misclassified). Deterministic per report so results are
# comparable across runs. attention 50 = NEUTRAL_ATTENTION (no webcam score).
READING_CONTEXT = {
    "audio_label": "silence",
    "attention_score": 50.0,
    "interaction_rate": 0.2,
    "audio_confidence": 0.9,
}


def _norm(text: str) -> str:
    import re

    t = " ".join(str(text).lower().split())
    return re.sub(r"[^a-z0-9 +\-/$%._]", " ", t)


def _matches(expected: str, candidate: str) -> bool:
    """Containment match on normalized strings (either direction)."""
    e, c = _norm(expected), _norm(candidate)
    if len(e) < 2 or len(c) < 2:
        return False
    return e in c or c in e


class _EmptyGraph:
    """Deterministic stand-in for the knowledge graph (no nodes to boost)."""

    nodes: dict = {}


def _run_screenshot(image_path: Path, label: dict) -> dict:
    img = cv2.imread(str(image_path))
    report: dict = {
        "id": str(label.get("id", image_path.stem)),
        "image": image_path.name,
        "mode": label.get("mode", "unknown"),
        "true_intent": label.get("true_intent", "unknown"),
        "theme": label.get("theme", ""),
        "image_loaded": img is not None,
    }
    if img is None:
        return report

    processed = preprocess_image(img)
    text = extract_text(processed) or ""

    sanitized = sanitize_text_for_storage(text)
    report["privacy_rejected"] = not sanitized.get("safe_to_store", False)
    if not sanitized.get("safe_to_store"):
        return report
    raw_text = strip_redaction_markers(sanitized.get("text", text))

    keywords = extract_keywords(raw_text, top_n=TEXT_TOP_KEYWORDS, graph=_EmptyGraph()) or {}

    expected = [str(c) for c in label.get("expected_concepts", []) or []]
    expected_clean = [e for e in expected if len(_norm(e)) >= 2]
    matched = {e: any(_matches(e, k) for k in keywords) for e in expected_clean}
    text_matched = {e: (_norm(e) in _norm(raw_text) if len(_norm(e)) >= 2 else False) for e in expected}

    report["text_recall"] = _ratio(text_matched)
    report["keyword_recall"] = _ratio(matched)
    kws = list(keywords)
    matched_kw = [k for k in kws if any(_matches(e, k) for e in expected_clean)]
    report["keyword_precision"] = round(len(matched_kw) / len(kws), 4) if kws else 0.0
    report["keyword_count"] = len(kws)
    report["top_keywords"] = kws[:8]
    report["ocr_text_chars"] = len(raw_text)
    report["ocr_text_preview"] = raw_text[:120]

    # Hierarchy: title / heading substrings present in the OCR text.
    hier = label.get("expected_hierarchy") or {}
    title = hier.get("title") or ""
    headings = [s.get("heading") for s in hier.get("sections") or [] if s.get("heading")]
    title_hit = bool(title) and _norm(title) in _norm(raw_text)
    heading_hits = [_norm(h) in _norm(raw_text) for h in headings]
    report["hierarchy"] = {
        "title_hit": title_hit,
        "heading_hits": heading_hits,
        "headings_expected": headings,
        "hierarchy_score": round((int(title_hit) + sum(1 for h in heading_hits if h)) / max(1, (1 if title else 0) + len(headings)), 4),
    }

    # Intent under the documented reading context.
    intent = predict_intent(
        ocr_keywords=keywords,
        audio_label=READING_CONTEXT["audio_label"],
        attention_score=READING_CONTEXT["attention_score"],
        interaction_rate=READING_CONTEXT["interaction_rate"],
        audio_confidence=READING_CONTEXT["audio_confidence"],
    )
    report["intent"] = {
        "predicted": intent.get("intent_label"),
        "true": label.get("true_intent"),
        "confidence": intent.get("confidence"),
        "source": intent.get("source"),
        "features": intent.get("features"),
        "correct": intent.get("intent_label") == label.get("true_intent"),
    }
    return report


def _ratio(hits: dict) -> float:
    return round(sum(1 for v in hits.values() if v) / len(hits), 4) if hits else 0.0


def _load_pairs() -> list[tuple[Path, dict]]:
    pairs = []
    ids = {}
    for png in sorted(GOLDEN_DIR.glob("*.png")):
        prefix = png.name.split("-")[0]
        if not prefix.isdigit() or prefix in ids:
            continue
        label = find_label(png, prefix)
        if label is None:
            print(f"  [WARN] no label found for {png.name}; skipped")
            continue
        ids[prefix] = png
        pairs.append((png, label))
    return pairs


def find_label(png: Path, prefix: str) -> dict | None:
    for lf in GOLDEN_DIR.glob(f"{prefix}-*-label.json"):
        try:
            return json.loads(lf.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [WARN] bad label {lf.name}: {e}")
    return None


def main() -> int:
    get_keyword_extractor()
    pairs = _load_pairs()
    if not pairs:
        print("No golden samples found. See GOLDEN_DATASET.md.")
        return 1

    print(f"Evaluating {len(pairs)} golden screenshots...\n")
    reports = [_run_screenshot(png, label) for png, label in pairs]

    agg = _aggregate(reports)
    _print_summary(reports, agg)

    OUT_DIR.mkdir(exist_ok=True)
    out = {
        "summary": agg,
        "reading_context": READING_CONTEXT,
        "reports": reports,
    }
    out_path = OUT_DIR / "golden_report.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nReport written -> {out_path}")
    return 0


def _aggregate(reports: list[dict]) -> dict:
    def mean(key):
        vals = [r.get(key, 0.0) for r in reports if r.get("image_loaded")]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    return {
        "n": len(reports),
        "image_loaded": sum(1 for r in reports if r.get("image_loaded")),
        "avg_text_recall": mean("text_recall"),
        "avg_keyword_precision": mean("keyword_precision"),
        "avg_keyword_recall": mean("keyword_recall"),
        "avg_hierarchy_score": mean("hierarchy_score"),
        "intent_accuracy": _intent_acc(reports),
        "intent_confusion": _confusion(reports),
        "by_mode": _by_mode(reports),
    }


def _intent_acc(reports: list[dict]) -> float:
    rows = [r for r in reports if "intent" in r and r.get("image_loaded")]
    return round(sum(1 for r in rows if r["intent"]["correct"]) / len(rows), 4) if rows else 0.0


def _confusion(reports: list[dict]) -> dict:
    rows = [r for r in reports if "intent" in r and r.get("image_loaded")]
    cm: dict = {}
    for r in rows:
        true, pred = r["intent"]["true"], r["intent"]["predicted"]
        cm.setdefault(true, {}).setdefault(pred, 0)
        cm[true][pred] += 1
    return cm


def _by_mode(reports: list[dict]) -> dict:
    out = {}
    for r in reports:
        if not r.get("image_loaded"):
            continue
        m = r.get("mode") or "unknown"
        out.setdefault(m, {"n": 0, "text_recall": [], "keyword_recall": [], "intent_ok": 0})
        b = out[m]
        b["n"] += 1
        b["text_recall"].append(r.get("text_recall", 0.0))
        b["keyword_recall"].append(r.get("keyword_recall", 0.0))
        if r.get("intent", {}).get("correct"):
            b["intent_ok"] += 1
    for b in out.values():
        b["avg_text_recall"] = round(sum(b["text_recall"]) / len(b["text_recall"]), 4)
        b["avg_keyword_recall"] = round(sum(b["keyword_recall"]) / len(b["keyword_recall"]), 4)
        del b["text_recall"], b["keyword_recall"]
    return out


def _print_summary(reports: list[dict], agg: dict) -> None:
    hdr = f"{'id':>3} {'mode':<15} {'intent(t/p)':<13} {'prec':>6} {'rec':>6} {'tRec':>6} {'hier':>6}"
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(reports, key=lambda x: x["id"]):
        print(
            f"{r['id']:>3} {r.get('mode','')[:15]:<15} "
            f"{r.get('true_intent','?'):>9}/{(r.get('intent') or {}).get('predicted','?'):<3} "
            f"{r.get('keyword_precision',0):>6.2f} {r.get('keyword_recall',0):>6.2f} "
            f"{r.get('text_recall',0):>6.2f} {(r.get('hierarchy') or {}).get('hierarchy_score',0):>6.2f}"
        )
    print("-" * len(hdr))
    s = agg
    print(f"OVERALL n={s['n']}  intent_acc={s['intent_accuracy']:.2f}  "
          f"prec={s['avg_keyword_precision']:.2f}  rec={s['avg_keyword_recall']:.2f}  "
          f"textRec={s['avg_text_recall']:.2f}  hier={s['avg_hierarchy_score']:.2f}")
    print("CONFUSION matrix (true -> predicted):")
    for t, preds in s["intent_confusion"].items():
        print(f"   {t:<9} -> {preds}")


if __name__ == "__main__":
    raise SystemExit(main())

