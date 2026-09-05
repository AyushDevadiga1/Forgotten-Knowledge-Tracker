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

### Added
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