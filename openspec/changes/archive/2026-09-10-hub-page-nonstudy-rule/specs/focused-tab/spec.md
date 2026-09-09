## MODIFIED Requirements

### Requirement: Focused tab gates the studying label

When a focused tab is available, the intent classifier SHALL treat the tab as ground truth of what the user is engaged with, overriding screen-wide OCR content. If `tab_relevance` (tab title+URL token overlap with the user's study concepts) is at or below the demotion threshold, a `studying` prediction SHALL be demoted to `passive` even when OCR content relevance is high. If `tab_relevance` is at or above the promotion threshold, a `passive`/`idle` prediction SHALL be promoted to `studying`. When no focused tab is available (non-browser or capture `None`), the classifier MUST retain today's OCR-only content bias behavior. The 6-feature model vector MUST remain unchanged. When the focused tab URL is a navigation-surface URL, the navigation-surface rule in the "Navigation-surface URLs are not study" requirement SHALL take precedence over this requirement's promotion behavior.

#### Scenario: Stale study tab in a non-study focused tab
- **WHEN** OCR content relevance is high (stale LeetCode tab visible on screen) but the focused tab title is "Google Careers" with no study-concept overlap
- **THEN** the prediction is demoted to `passive`

#### Scenario: Focused study tab promotes a passive prediction
- **WHEN** the focused tab title/URL strongly overlap study concepts and the base prediction is `passive` or `idle` and the focused tab URL is NOT a navigation-surface URL
- **THEN** the prediction is promoted to `studying`

#### Scenario: Non-browser foreground window
- **WHEN** no browser tab is focused (e.g. an IDE) and the focused tab capture returns `None`
- **THEN** the OCR-only content bias applies exactly as before the change

## ADDED Requirements

### Requirement: Navigation-surface URLs are not study

The system SHALL recognize a class of focused-tab URLs that are navigation surfaces rather than study content, and SHALL override any `studying` prediction (whether from the classifier or promoted by the tab gate) to a non-study label when the focused tab URL is one of these surfaces. A navigation surface SHALL be identified structurally, host-agnostically, by its URL path being a root/home/navigation path (`""`, `/`, `/home`, `/feed`, `/explore`, `/browse`, `/trending`), NOT by a host denylist, so the rule generalizes to any host. The system SHALL demote such a `studying` prediction to `idle` when the user's interaction rate is below 1.0 input events/second, and to `passive` otherwise. The rule SHALL apply ONLY when a focused tab URL is present: cycles with no focused tab (desktop windows, or a browser whose capture returned no URL) MUST retain the existing behavior unchanged. The system MAY recognize additional navigation-surface patterns as an explicit, documented heuristic extension; such extensions SHALL remain host-agnostic and SHALL NOT be created per-screen for the golden dataset.

#### Scenario: Study-adjacent hub root without interaction
- **WHEN** the focused tab URL is a host root (e.g. `https://www.kaggle.com/`), the base prediction is `studying`, OCR and tab content are study-adjacent, and interaction rate is below 1.0/s
- **THEN** the prediction is demoted to `idle` regardless of classifier or tab-promotion

#### Scenario: Hub root with ongoing interaction
- **WHEN** the focused tab URL is a host root, the base prediction is `studying`, and interaction rate is at or above 1.0/s
- **THEN** the prediction is demoted to `passive`

#### Scenario: Tab-promoted studying on a hub is overridden
- **WHEN** a focused tab URL is a navigation surface that the tab gate would otherwise promote to `studying`
- **THEN** the prediction is NOT `studying`; the navigation-surface rule wins over the tab promotion

#### Scenario: Content path is not a hub
- **WHEN** the focused tab URL has a non-root content path (e.g. a study article or a careers listing under `/jobs/...`)
- **THEN** the navigation-surface rule does not fire and the tab/OCR gate behavior is unchanged

#### Scenario: Non-hub host root
- **WHEN** a focused tab URL's path is a root/home/navigation path but the user's tab-ground-truth study gate already agrees (e.g. a study-relevant root page with sustained activity)
- **THEN** the rule still applies; the root path is treated as a navigation surface in both interaction tiers

#### Scenario: No focused tab URL
- **WHEN** no focused tab URL is present (desktop window, or browser capture returned no URL)
- **THEN** the navigation-surface rule does not fire and all existing behavior is unchanged
