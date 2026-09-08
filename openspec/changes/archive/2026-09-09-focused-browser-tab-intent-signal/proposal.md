## Why

Silent studying is no longer dropped (intent_acc 0.07 -> 0.80), but the golden dataset still mislabels two screens where the focused app is NOT study: `012` (idle, Kaggle home) and `014` (passive, Google Careers with a stale LeetCode tab visible). Content relevance alone cannot separate them - a real studying sample (`002`) scores the same relevance as the negatives, and embeddings rank the negatives above some genuine studying frames. The missing information is *where the user's attention is*, which only the focused window/tab exposes.

## What Changes

- **New focused-tab capture (`focused-tab` capability).** A new `tracker_app/tracking/focused_tab.py` reads the foreground browser's focused tab (title + URL) via Windows UI Automation (pywinauto), gated on **process name** (`chrome.exe`, `msedge.exe`, `firefox.exe`) because the `Chrome_WidgetWin_1` window class is also used by Electron apps. Firefox's tab strip is not UIA-exposed, so it degrades to window-title parsing. Any failure (non-Windows, UIA unavailable, foreground window not a browser) returns `None` cleanly.
- **Rule-level "tab overrides OCR" gate.** `predict_intent` gains optional `active_tab_title` / `active_tab_url` kwargs. When a browser tab is focused, `tab_relevance` (tab title+URL vs study concepts) gates the content bias: `tab_relevance <= RELEVANCE_LOW` demotes studying->passive **even when OCR relevance is high** (fixes `014`: focused "Google Careers" while OCR sees the stale LeetCode tab); `tab_relevance >= RELEVANCE_HIGH` promotes passive/idle->studying. Non-browser or no tab falls back to today's OCR-only bias. The 6-feature model contract is untouched.
- **Persistence.** `window_title` is already captured and stored; focused tab title+URL are added so the signal is auditable and available to the future all-tabs phase (schema-ready via a `focused_tab` JSON-ish column, capture flag off by default).
- **Golden harness.** Labels gain `focused_tab_title` / `focused_tab_url`; the runner passes them to `predict_intent`, so the gate is measured against the hand-labeled dataset.

## Capabilities

### New Capabilities
- `focused-tab`: how the active browser tab is discovered on Windows (UIA + process gating + Firefox fallback), how its title/URL flow into intent classification as a rule-level gate, and how it is persisted alongside existing telemetry.

### Modified Capabilities
None - no `openspec/specs/` main specs exist yet; delta specs live under change dirs (repo convention).

## Impact

- `tracker_app/tracking/focused_tab.py` (new) - UIA capture module.
- `tracker_app/tracking/intent_module.py` - `predict_intent` kwargs + tab-overrides-OCR gate.
- `tracker_app/tracking/loop.py` - call focused-tab capture; pass tab into `predict_intent`; persist title/URL.
- `tracker_app/db/models.py`, `tracker_app/db/migrations.py` - focused-tab persistence column.
- `tools/golden_eval.py`, `data/golden/*-label.json` - focused_tab fields passed through.
- `requirements.txt` - `pywinauto` (Windows-only marker).
- New tests in `tracker_app/tests/` (focused_tab unit + predict_intent gate + golden harness).
