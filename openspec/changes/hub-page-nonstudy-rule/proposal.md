## Why

The tab gate closed 014 but left 012 (Kaggle home) as a documented limit: the keyboard see the screen as studying because Kaggle home is dense with study-adjacent text, and the focused tab "Kaggle: Your Machine Learning and Data Science Community" scores `tab_relevance 1.0`. Evidence shows the base classifier itself predicts `studying` (0.99 confidence, 15 keywords, avg 0.707; `content_relevance 0.066` sits above `RELEVANCE_LOW`), so no amount of tab-only logic fixes it. The missing invariant is structural: a domain root / home / feed URL is a navigation surface, not study content. It must be treated as non-study regardless of how study-adjacent the tab and OCR look, unless the user is actively interacting.

## What Changes

- Add a structural, host-agnostic navigation-surface rule to `predict_intent`: when the focused tab URL's path is a root/home/feed navigation path (`""`, `/`, `/home`, `/feed`, `/explore`, `/browse`, `/trending`), a `studying` prediction is demoted to `idle` when interaction rate is below the idle threshold (1.0/s) and to `passive` otherwise. This runs AFTER the classifier and the tab gate and overrides both — the hub demotes tab-promoted `studying` too (navigation surfaces never become "ground-truth study", reversing the tab-as-ground-truth overreach).
- Keep the curated seed patterns minimal and explicit as an extensible heuristic for navigation surfaces that do not live at a root/home path (e.g. channel or feed pages under a different path). The rule is NOT a host denylist: its mechanism generalizes to any future hub without a list update.
- No-tab and desktop-window cycles are untouched: the rule only fires when a focused tab URL is present, so OCR-only windows (001-013, 015) behave identically.
- Golden outcome: 012 becomes `idle`/correct; reported intent accuracy rises 0.87 -> 0.93. `GOLDEN_DATASET.md` section 7 and the 012 golden test flip from "documented hub-page limit" to "fixed by navigation-surface rule".

## Capabilities

### New Capabilities
<!-- none: the behavior belongs to the existing focused-tab intent gate -->

### Modified Capabilities
- `focused-tab`: the "Focused tab gates the studying label" requirement is extended — a study-adjacent tab whose URL is a navigation surface (root/home/feed path) is demoted from `studying` regardless of `tab_relevance`, with an interaction-based `idle`/`passive` split. A new requirement is added for the structural navigation-surface rule and its generalization constraints.

## Impact

- `tracker_app/tracking/intent_module.py` — new `is_hub_url`/navigation-surface predicate + the post-gate hub demotion in `predict_intent` (new `rules+hub` source).
- `tracker_app/tests/test_intent_tab_gate.py` — new hub rule tests (idle/passive split, tab-promotion override, content-path preservation, non-hub-root preservation, no-URL preservation, path boundaries).
- `tracker_app/tests/test_golden_tab_signal.py` — `012` expected outcome flips to `idle`/correct.
- `tools/golden_eval.py` — unchanged (already forwards `focused_tab_url`); measured intent_acc recomputed.
- `GOLDEN_DATASET.md`, `CHANGELOG.md` — documentation updates.
- No schema migration, no new dependency, no loop changes.
