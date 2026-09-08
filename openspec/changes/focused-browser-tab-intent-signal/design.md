## Context

`predict_intent` currently applies an OCR-only content-relevance bias (intent_module.py): demote studying when on-screen keyword overlap with the knowledge graph is <= `RELEVANCE_LOW`, promote passive/idle when >= `RELEVANCE_HIGH`. Golden evaluation proved this cannot separate the two remaining mislabels (`012` idle Kaggle-home, `014` passive Google Careers with a stale LeetCode tab): a real studying sample scores the same relevance, and embeddings rank the negatives above genuine studying. The missing signal is *what the user is focused on*. The loop already captures `window_title` per cycle via `win32gui.GetForegroundWindow` (loop.py:120) and persists it (MultiModalLog.window_title, FeedbackTrainingSample.window_title), but never feeds it to intent.

## Goals / Non-Goals

**Goals:**
- Read the focused browser tab (title + URL) on Windows with UIA, gated to real browsers by process name.
- Make a focused tab override OCR in the content bias so `014` demotes and study-focused tabs promote.
- Persist tab title/URL with existing telemetry, schema-ready for a future all-tabs snapshot.
- Keep the 6-feature model contract and OCR-only behavior for non-browser windows byte-identical.

**Non-Goals:**
- No new model feature (the "7th feature" idea was shelved - Approach A chosen over B).
- No full-tab-list capture this phase (capture flag stays off; schema only).
- No Firefox tab-strip support via UIA (not exposed); Firefox uses the window-title fallback.
- No browser extension / CDP channel.

## Decisions

- **UIA via pywinauto** over raw COM or CDP. pywinauto wraps UIAutomation with a stable high-level tree API; it is Windows-only and already `requirements.txt`-compatible (`platform_system == "Windows"`). Probed on this machine: `TabItem` and `Edit` (address-bar) controls are enumerable inside `Chrome_WidgetWin_1` windows.
- **Process-name gating, not window class.** `Chrome_WidgetWin_1` is shared by Chrome, Edge, and Electron apps. Gate on `chrome.exe` / `msedge.exe` / `firefox.exe` by inspecting the foreground HWND's process.
- **Focused tab = title + URL.** Query the UIA tree for the address-bar Edit (URL) and the selected `TabItem` (title). If the tree yields no tab selection, fall back to window title. Firefox: no UIA tab strip -> parse the window title only.
- **`tab_relevance` reuses `compute_content_relevance`.** Treat the tab title+URL as a 2-item dict of phrases scored 1.0 and reuse the existing concept-token overlap function - no new similarity machinery, deterministic, consistent with the OCR path.
- **Tab overrides OCR, one gate.** The bias becomes: if a focused tab is present, decide solely on `tab_relevance` (low -> demote studying to passive; high -> promote passive/idle to studying); otherwise use OCR relevance exactly as today. This is the semantic the user approved and the only one that fixes `014` (whose OCR relevance is 0.264, above LOW, so a both-low gate would never fire).
- **Persistence via a `focused_tab` column on `multi_modal_logs`.** Add through the existing migrations runner (`013` is the current tail). JSON text holding `{title, url}`; NULL/empty when absent. Parallel single `focused_tab` fields on `feedback_training_samples` are deferred (schema-ready only).
- **Privacy reuse.** Pass the tab title/URL through `is_sensitive_window` before persistence; on sensitive, store nothing.
- **Harness.** `tools/golden_eval.py` reads `focused_tab_title`/`focused_tab_url` from each label and forwards them; report gains `source`, `tab_relevance`.

## Risks / Trade-offs

- **UIA tree shape varies by Chrome version / localization.** The address-bar Edit may be named differently -> [Mitigation] defensive: walk by ControlType Edit under the browser window; on any miss, `None` (no raise), and window-title fallback.
- **Per-cycle UIA query cost.** UIA can be slow if the whole tree is walked every 5s -> [Mitigation] capture only when the foreground HWND changed since last sample (memoize on hwnd); UIA itself is ordinal for a focused-window subtree.
- **`tab_relevance` false positives.** A hub page whose URL echoes a concept (Kaggle home) stays studying -> [Mitigation] accepted as a documented limit (proposal); the rule is deliberately tab-as-ground-truth.
- **Firefox is degraded (title only, no URL).** -> [Mitigation] explicit in proposal/spec; window title still carries the tab title for most Firefox sessions.
- **Golden images carry no real window context.** The harness passes synthetic label fields, so the golden number reflects the gate logic not the real capture -> [Mitigation] unit tests for the capture module run on real UIA where available (local dev), and the harness test asserts the gate semantics.

## Migration Plan

- Add `focused_tab` column via a new migration entry (`014_focused_tab`) in `tracker_app/db/migrations.py` (guarded ADD COLUMN, existing runner applies on startup - no manual step).
- Add `pywinauto` to `requirements.txt` under `platform_system == "Windows"`; non-Windows imports of `focused_tab.py` return `None`.
- Rollback: revert the migration entry + column reference and the `predict_intent` kwargs; the loop already tolerates `predict_intent` exceptions (logger.warning + fallback). `focused_tab.py` absence must not break import of `loop.py` (lazy import inside the capture call).
