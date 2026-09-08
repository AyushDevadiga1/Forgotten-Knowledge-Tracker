# Focused Tab Specification

## Purpose

Exposes the browser tab the user is actually focused on (title + URL) so intent classification can tell genuine study from screens that merely show study-adjacent text (e.g. a careers page with a stale LeetCode tab).

## Requirements

### Requirement: Focused browser tab is captured on Windows

The system SHALL read the foreground browser window's focused tab (title and URL) using Windows UI Automation when the foreground window is a supported browser. Supported browsers SHALL be identified by process name (`chrome.exe`, `msedge.exe`, `firefox.exe`), NOT by window class, because the `Chrome_WidgetWin_1` class is shared with Electron apps. When the foreground window is not a browser, or capture fails for any reason (non-Windows platform, UIA unavailable, process exited), the system MUST produce a `None` result without raising and without blocking the tracking loop.

#### Scenario: Chrome in the foreground
- **WHEN** the foreground window belongs to `chrome.exe` and its focused tab has title "Google Careers" and URL `https://careers.google.com/jobs`
- **THEN** capture returns that title and URL

#### Scenario: Electron app with a browser-like window class
- **WHEN** the foreground window has class `Chrome_WidgetWin_1` but its process name is not a supported browser
- **THEN** capture returns `None` and does not expose the app's tabs

#### Scenario: Firefox fallback
- **WHEN** the foreground window belongs to `firefox.exe` and its tab strip is not exposed via UIA
- **THEN** capture falls back to parsing the window title and returns that as the focused tab title, with no URL

#### Scenario: UIA unavailable
- **WHEN** UI Automation cannot be queried on the machine
- **THEN** capture returns `None` without raising

### Requirement: Focused tab gates the studying label

When a focused tab is available, the intent classifier SHALL treat the tab as ground truth of what the user is engaged with, overriding screen-wide OCR content. If `tab_relevance` (tab title+URL token overlap with the user's study concepts) is at or below the demotion threshold, a `studying` prediction SHALL be demoted to `passive` even when OCR content relevance is high. If `tab_relevance` is at or above the promotion threshold, a `passive`/`idle` prediction SHALL be promoted to `studying`. When no focused tab is available (non-browser or capture `None`), the classifier MUST retain today's OCR-only content bias behavior. The 6-feature model vector MUST remain unchanged.

#### Scenario: Stale study tab in a non-study focused tab
- **WHEN** OCR content relevance is high (stale LeetCode tab visible on screen) but the focused tab title is "Google Careers" with no study-concept overlap
- **THEN** the prediction is demoted to `passive`

#### Scenario: Focused study tab promotes a passive prediction
- **WHEN** the focused tab title/URL strongly overlap study concepts and the base prediction is `passive` or `idle`
- **THEN** the prediction is promoted to `studying`

#### Scenario: Non-browser foreground window
- **WHEN** no browser tab is focused (e.g. an IDE) and the focused tab capture returns `None`
- **THEN** the OCR-only content bias applies exactly as before the change

### Requirement: Focused tab is persisted with telemetry

The system SHALL record the focused tab title and URL alongside the existing `window_title` telemetry for each capture cycle, and SHALL reuse the existing sensitive-window privacy gate so a sensitive browser session never has its tab title/URL persisted. Persistence SHALL be schema-ready for a future full-tab snapshot without changing behavior today (column exists; full-list capture is off by default).

#### Scenario: Sensitive browser session
- **WHEN** the focused window passes the sensitive-window check
- **THEN** no tab title or URL is persisted

#### Scenario: Persisted with telemetry
- **WHEN** a cycle logs its multi-modal row
- **THEN** the focused tab title and URL (when present) are stored alongside `window_title` and the intent label

### Requirement: Golden harness measures the tab gate

The golden evaluation harness SHALL pass each labeled screenshot's `focused_tab_title` and `focused_tab_url` (when present in the label) into `predict_intent`, and SHALL report the `source` and `tab_relevance` alongside the existing per-screenshot intent fields.

#### Scenario: Label carries a focused tab
- **WHEN** a golden label includes `focused_tab_title` / `focused_tab_url` and the screenshot's intent is evaluated
- **THEN** the runner passes those values to `predict_intent` and records the resulting `source` and `tab_relevance` in the report
