## 1. Capture module (new `tracker_app/tracking/focused_tab.py`)

- [ ] 1.1 Add `pywinauto` to `requirements.txt` with a `platform_system == "Windows"` marker and skip on other platforms
- [ ] 1.2 Implement `get_focused_tab(fallback_ok=True) -> FocusedTab | None` that takes the foreground HWND, resolves its process name, and returns `None` (never raises) for non-browsers, non-Windows, UIA failures, or unexpected tree shapes
- [ ] 1.3 Resolve the focused tab's URL from the address-bar `Edit` (ControlType Edit search) and title from the selected `TabItem`; keep the subtree walk defensive so any miss degrades to `None`
- [ ] 1.4 Support the Firefox fallback: when the foreground process is `firefox.exe` (or the tab strip is not exposed), parse the window title as the tab title and set URL to `None`
- [ ] 1.5 Lazy-import the module inside the capture call so `loop.py` imports cleanly when `pywinauto` is not installed

## 2. Intent gate (tracking/intent_module.py)

- [ ] 2.1 Extend `predict_intent` with optional `active_tab_title: str | None`, `active_tab_url: str | None` kwargs without changing the existing required signature or the 6-feature model vector
- [ ] 2.2 Compute `tab_relevance` from a 2-item phrases dict `{tab_title: 1.0, tab_url: 1.0}` reusing `compute_content_relevance` (no new similarity machinery)
- [ ] 2.3 Implement the tab-overrides-OCR gate: with a focused tab, `tab_relevance <= RELEVANCE_LOW` demotes studying->passive even when OCR relevance is high; `>= RELEVANCE_HIGH` promotes passive/idle->studying; no tab -> existing OCR-only bias unchanged
- [ ] 2.4 Report `source: "rules+tabs"` and `tab_relevance` in the returned intent dict; `source` stays `"rules+content"` when no tab is present

## 3. Loop integration (tracking/loop.py + activity_monitor.py)

- [ ] 3.1 Call `get_focused_tab` in the capture path, memoized per foreground HWND change (avoid per-cycle UIA cost)
- [ ] 3.2 Pass tab title/URL into the `predict_intent` call site and record `tab_relevance`/`source` on diagnostics (log line)
- [ ] 3.3 Persist the focused tab title/URL through the same row as `window_title`, gated by the existing `is_sensitive_window` check so sensitive sessions store nothing

## 4. Persistence (db/models.py, db/migrations.py, web/feedback)

- [ ] 4.1 Add a `focused_tab` text column (JSON `{title, url}`) to `MultiModalLog` in `db/models.py`
- [ ] 4.2 Add migration entry `014_focused_tab` to `db/migrations.py` (guarded ADD COLUMN, appended after `013_feedback_used_in_training`)
- [ ] 4.3 Add nullable `focused_tab_title` / `focused_tab_url` columns to the feedback training sample persistence path (schema-ready; not gated on in training yet)

## 5. Golden harness (tools/golden_eval.py + data/golden)

- [ ] 5.1 Accept optional `focused_tab_title` / `focused_tab_url` in each golden label and pass them into `predict_intent`
- [ ] 5.2 Record `source` and `tab_relevance` per screenshot in the intent report section
- [ ] 5.3 Annotate `012` (Kaggle home, idle) and `014` (Google Careers, passive) labels with their synthetic focused-tab fields; update `GOLDEN_DATASET.md` to record the intent_acc effect and the `012` hub-page limit

## 6. Tests (tracker_app/tests)

- [ ] 6.1 Unit-test `get_focused_tab` with a fake process-describer/UIA double: non-browser HWND -> None, supported browser HWND -> title+URL, Firefox wobble -> title-only, exception -> None (no raise)
- [ ] 6.2 Unit-test the `predict_intent` gate: stale-tab demotion (014 shape), study-title promotion, non-browser no-tab fallback preserves OCR-only behavior, `tab_relevance` in result
- [ ] 6.3 Test the `MultiModalLog.focused_tab` persistence + migration guard and that sensitive windows store empty tab fields
- [ ] 6.4 Extend the golden harness test to assert 014 demotes to passive (studying preserved) and the captured-gate path reports `source` `"rules+tabs"`

## 7. Docs

- [ ] 7.1 Add CHANGELOG entry describing the focused-tab signal, the tab-overrides-OCR rule, migration `014_focused_tab`, and the new `pywinauto` dependency
- [ ] 7.2 Update `GOLDEN_DATASET.md` ?7 to reflect the tab-gate fix for `014` and the remaining `012` limit
