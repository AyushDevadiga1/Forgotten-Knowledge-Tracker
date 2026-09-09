## Context

See proposal.md - Why. `predict_intent` (tracker_app/tracking/intent_module.py) already applies, in order: classifier/rules -> OCR content bias -> focused-tab gate (`rules+tabs`, demote/promote on `tab_relevance`). The golden set contains exactly two focused-tab URLs (012 `https://www.kaggle.com/`, 014 `https://careers.google.com/jobs/results/...`); all other images are desktop windows with no URL. The tab gate cannot fix 012 because the base classifier already predicts `studying` (0.99, content_relevance 0.066) and the Kaggle-home tab scores `tab_relevance 1.0`.

## Goals / Non-Goals

**Goals:**
- Add a single, structural navigation-surface predicate to the intent gate that generalizes to any host.
- Demote `studying` to non-study on navigation-surface URLs, overriding both classifier and tab-promotion outcomes.
- Interaction-based split (idle vs passive) consistent with the existing idle rule semantics.
- Keep the 6-feature model contract and all no-URL paths byte-identical.

**Non-Goals:**
- No host denylist and no curated per-site table.
- No new model feature, no schema change, no new dependency, no tracking-loop change (`active_tab_url` is already passed into `predict_intent`).
- No OCR/structure inference for desktop windows without a URL.
- No dwell/time-series signal (a separate, later concern; the loop has no cycle history feeding `predict_intent` today).

## Decisions

- **Structural path predicate over a host denylist.** `is_navigation_surface(url) -> bool` normalizes the URL and returns True when its path segment is empty, `/`, or one of `/home`, `/feed`, `/explore`, `/browse`, `/trending`. Host-agnostic by construction: any future hub with a root/home path is caught without a list update. Alternative considered and rejected: per-host denylists (Kaggle, GitHub, ...) - validated by exactly one golden data point, i.e. golden-built overfit.
- **Fires after the tab gate and overrides it.** The hub rule runs last: whichever upstream path produced `studying` (classifier, rules+content, or `rules+tabs` promotion), a navigation-surface URL rewrites it. This reverses the tab-as-ground-truth overreach only for navigation surfaces, and is scoped narrowly (the existing promotion scenario in the focused-tab spec is annotated to require a non-navigation-surface URL).
- **Interaction split at 1.0/s** (constant `HUB_IDLE_INTERACTION = 1.0`). `interaction_rate < 1.0` -> `idle`; otherwise -> `passive`. This mirrors the existing `_RULE_MAP` idle rule (`ir < 1` -> idle) so a navigation surface with meaningful activity is `passive` (browsing), never `idle`. Result `source` becomes `rules+hub`.
- **Heuristic extension is a documented, host-agnostic set.** Any future navigation-surface patterns extend the path/payload set in one module constant; entries MUST be host-agnostic. Explicitly no per-screen entries for golden samples (012 gets fixed by the generic `/` path, not by a `kaggle.com` entry).
- **Golden harness unchanged.** `golden_eval.py` already forwards `focused_tab_url`; only its measured number and the `012` expectation change.

## Risks / Trade-offs

- Content genuinely served at a root path (a single-page article at `example.io/`) is demoted on navigation-surface shape. -> Mitigation: the two-tier interaction split keeps actively-engaged users at `passive`, and the rule never fires without a URL; content-at-root remains a documented residual.
- Portals serving navigation at non-root paths (e.g. a dashboard under `/dashboard`) escape the structural set. -> Mitigation: recorded as an explicit heuristic-extension point per the spec; acceptable until evidence shows it matters.
- The golden harness pins `interaction_rate 0.2` for every image, so `idle` is what 012 produces there; the live loop's split may produce `passive` for interactive hub browsing - both satisfy the spec.
- Deliberately no change to the tab-gate threshold values; the hub rule is additive and only demotes.

## Migration Plan

- Pure in-code rule; no migration. Rollback: revert the `predict_intent` block and `is_navigation_surface` predicate; all other logic unchanged.
