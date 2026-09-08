# Changelog

All notable changes to FKT are documented here.

## Unreleased

### Fixed
- `696188d` docs: correct architecture discrepancies (DB name, frontend, endpoints, ERD)
- `1fc704d` fix(security): add table allowlist for f-string SQL in migrations
- `1fc704d` fix(quality): add logging to 9 pass-in-except blocks
- `2a796f8` fix: CI pynput/psutil stub for headless CI
- `02e6091` fix: 6 additional CI failures from weak .env config
- `77b4964` fix: trend boundary test mock _utcnow instead of datetime
- `824891f` fix: remove BOM markers from source files
- `21342a1` fix: broken launcher check command, update stale frontend status
- `44d6b60` fix(ocr): preserve real screen text (PSM 3, no confidence gate, grayscale-only preprocessing); concept recall 0.00 -> 0.80 on golden set
- `a6697b5` fix(quality): printable unicode no longer treated as control characters in OCR coherence check

### Added
- `319c876` feat(intent): focused-browser-tab signal (Windows UIA) overrides OCR bias; tab-overrides-OCR rule in `predict_intent`, migration `014_focused_tab` (tab columns on `intent_predictions`, `multi_modal_logs`, `feedback_training_samples`), new `pywinauto` dependency; golden intent_acc 0.87 (014 fixed, 012 documented hub-page limit)
- `360b97f` feat(golden): golden OCR eval harness + hand-labelled dataset (data/golden/, 001-015) with baseline report
- `e1cd358` feat(golden): harness seeds intent concepts from studying labels and reports content relevance per screenshot
- `0f0e09a` feat(intent): content-aware rule bias (screen keywords vs study concepts) demotes irrelevant studying, promotes relevant passive
- `7ca38e6` test(intent): content-relevance helpers and rule bias coverage
- `ed7e9f4` docs(proposal): SLM/VLM offline extraction upgrade path (PROPOSAL.md)
- `36ca170` feat(intent): silent-reading cluster added to synthetic intent training data
- `4be4bca` feat: extract 30+ magic numbers to named constants (constants.py)
- `44d5191` build: add coverage config with 60% fail-under threshold
- `2a796f8` style: add ruff linting config + CI lint job
- `f7fb84d` docs: add 9-phase diagnosis report, CURRENT-PROBLEMS.md
- `5d11067` docs: update README, add project health analysis
- `824891f` docs: add project metrics tracking (snapshots, changelog, health)
- `d0ab77b` docs: add GIGO remediation diagnosis and refresh dependency graph
- `2bcaa66` feat(gigo): Phase 0/1 - guarded DB reset tool (`reset_database`), seed-clear aligned to the purge table list
- `4b68fe1` feat(gigo): Phase 2 - optional attention (no fabricated score instead of hardcoded 60/50), full excerpt persistence (no 80/200-char truncation), webcam-unavailable persistence gate

### Changed
- `6dadeff` docs: rewrite README for a broader audience with the current feature set
- `d2d6011` docs: rename documentation/ to documents/, drop stale diagnosis file, refresh dependency graph
- `1891166` chore: remove unused filelock and pillow from requirements
- `6cf52b0` chore: ignore local agent configuration folders
- `0a356e9` style: remove internal phase/tracker references from code comments
- `ee5199d` chore: remove dead generate_secrets.py (unused Fernet key generation)
- `2a796f8` style: ruff auto-fix 476 issues + reformat 74 files
- `4be4bca` refactor: replace hardcoded thresholds with constants across 13 files

## Previous Sessions

- Extraction pipeline refactor (6 atomic commits)
- Full codebase audit (24 issues, 15+ commits)
- Concept filtering, security hardening, SM-2 fixes