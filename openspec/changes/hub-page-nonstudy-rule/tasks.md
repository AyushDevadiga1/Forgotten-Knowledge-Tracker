## 1. Navigation-surface predicate (TDD)

- [x] 1.1 Add host-agnostic `is_navigation_surface(url) -> bool` to intent_module.py with a structural path set: empty path, `/`, `/home`, `/feed`, `/explore`, `/browse`, `/trending`
- [x] 1.2 Unit tests for the predicate: root/host-only, each structural path, query-string suffix, port, case normalization, and non-navigation paths (`/problems/two-sum/`, `/jobs/results/`, `/competitions/`, `/dashboard`) return False
- [x] 1.3 Unit test: the predicate has no host dependency (same path set is navigation-surface for any host)

## 2. predict_intent hub demotion (TDD)

- [x] 2.1 Implement the post-gate hub rule in `predict_intent`: after the tab gate, when `active_tab_url` is a navigation surface and the prediction is `studying`, demote to `idle` when `interaction_rate < HUB_IDLE_INTERACTION` (=1.0) else `passive`, and set `source` to `rules+hub`
- [x] 2.2 Tests: classifier-`studying` + hub root + interaction 0.2 -> `idle`, source `rules+hub`; interaction 5.0 -> `passive`; exact-boundary interaction 1.0 stays `passive` (inclusive)
- [x] 2.3 Test: tab-promoted `studying` on a hub URL is overridden to non-study (hub wins over tab promotion)
- [x] 2.4 Tests: content-path URL (`/competitions/...`) stays `studying`; non-hub root host (e.g. `careers.google.com` with content path) is unchanged; no URL (no tab) is unchanged; a `passive`/`idle` base label on a hub is NOT further demoted

## 3. Golden + documentation

- [x] 3.1 Update `test_golden_012_kaggle_tab_signal_captured` to assert `idle`/correct (flips the documented-limit posture); keep assertions that the tab signal itself is captured
- [x] 3.2 Run `tools/golden_eval.py`, confirm intent_acc 0.87 -> 0.93 (012 fixed, 14/15), and regenerate `outputs/golden_report.json`
- [x] 3.3 Update `GOLDEN_DATASET.md` section 7: 012 no longer a limit; document the structural navigation-surface rule, the host-agnostic generalization, and the residual (content-at-root, non-root portals)
- [x] 3.4 Add CHANGELOG.md entry

## 4. Verification

- [x] 4.1 Run the focused-tab + intent test files, then the full pytest suite (expect 484 + new hub tests green)
- [x] 4.2 `openspec validate` on this change and `openspec validate --all` (3 specs)
- [x] 4.3 Confirm - no schema, dependency, or loop change is part of this diff
