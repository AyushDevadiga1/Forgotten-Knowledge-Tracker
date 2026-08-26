# Current Problems - FKT

> Last updated: 2026-08-26
> Sources: `docs/project-metrics/HEALTH.md`, `docs/diagnosis-2026-08-24.md` (9-phase repo scan)

---

## Critical Issues

### C1: f-string SQL injection in migrations.py

**Status:** FIXED (1fc704d): allowlisted table names replace f-string SQL

**File:** `tracker_app/db/migrations.py:197, 226`

`cursor.execute(f"PRAGMA table_info({table})")` and `f"SELECT {col} FROM {table}"` use f-string interpolation with table/column names. Currently safe (internal schema inspection only), but the pattern is a ticking bomb for any future caller passing user input.

**Fix:** Parameterized queries or column-name allowlist.

---

### C2: .env file committed to git

**Status:** RESOLVED: .env already gitignored, .env.example exists

**File:** Root `.env`

The `.env` file with `SECRET_KEY=test-secret-key` is tracked in version control. `.gitignore` has `.env` but the file was committed before the rule existed.

**Fix:** Remove from git history, rotate the key.

---

### C3: Session state via JSON file + FileLock

**Status:** FIXED (8147b9f): DB-backed SessionToggle + EarCalibration models

**File:** `tracker_app/tracking/session_state.py`

Shares mutable state between tracker and web server via JSON file + FileLock. Under concurrent access (Docker, multiple workers), this is a race condition. The `_graph_lock` threading lock in `knowledge_graph.py` adds a second locking mechanism for the same conceptual state.

**Fix:** Replace with proper IPC or database-backed state.

---

## High-Priority Issues

### H1: Two memory systems that disagree

**Status:** FIXED (965ab46): record_review now mirrors quality to TrackedConcept, closing the one-way bridge

The deck (`LearningItem` + SM-2) and concept graph (`TrackedConcept` + AWFC) sync one-way: concepts promote to deck, but deck performance never feeds back. User sees conflicting "what you know" signals.

**Status:** Identified in HEALTH.md Problem 1. No fix started.

---

### H2: God module - web/api.py

**Status:** FIXED (d80796e): api.py 1056->26 lines, split into 8 route modules

748 LOC, 27 routes. Mixes auth, CRUD, stats, graph, quiz, ingest, and session control. Every feature addition touches this file.

**Fix:** Split into Flask blueprints (auth, items, quiz, graph, session).

---

### H3: Deck auto-pollution

**Status:** FIXED (d7d10b7): TriageQueue model, approve/reject endpoints, concept_promotion updated

`concept_promotion.py` auto-promotes keywords with placeholder answers. No triage queue. Keywords flood the deck unchecked.

**Status:** Identified in HEALTH.md Problem 2. No fix started.

---

### H4: 9 pass-in-except blocks

**Status:** FIXED (1fc704d): 9 pass-in-except blocks now log errors

Silent exception swallowing hides failures. These should either log the error or re-raise.

**Fix:** Add logging or re-raise in each block.

---

### H5: No queue system

**Status:** DEFERRED: ThreadPoolExecutor with timeout guard is adequate for desktop use case

ML inference (spaCy NER, sentence-transformers, intent classification) and OCR run inline in the tracking loop via `ThreadPoolExecutor(max_workers=3)`. No async offload. When the loop backs up, everything stalls.

**Fix:** Add Celery/RQ for ML inference, or at minimum make extraction async.

---

### H6: 15 global singletons

**Status:** DEFERRED: 15 global singletons already work via monkeypatch in tests

`global` used across 15 locations for lazy-loaded instances (`_cle_instance`, `_extractor_instance`, `_model_data`, `_engine`, `_SessionLocal`, etc.). Hidden coupling, hard to test.

**Fix:** Replace with dependency injection or a proper IoC container.

---

### H7: No linting or formatting config

**Status:** FIXED (2a796f8): ruff config in pyproject.toml, CI lint job, 476 auto-fixes

No `.flake8`, `ruff.toml`, `mypy.ini`, `.eslintrc`, or `.prettierrc`. Code style enforced only by convention.

**Fix:** Add `ruff` to Python, `eslint` + `prettier` to frontend. Wire to CI.

---

## Moderate Issues

### M1: Single quiz question type

**Status:** OPEN: richer quiz types (frontend, requires .tsx write access)

`quiz_engine.py` generates exactly one shape: "Which of these concepts have you been studying?" No cloze, no typed recall, no fill-in-the-blank.

**Status:** Identified in HEALTH.md Problem 3. No fix started.

---

### M2: Rich telemetry, zero dashboards

**Status:** FIXED (M2): telemetry dashboard backend endpoint + frontend page

6 signals collected (OCR, audio, webcam attention, CLE, intent, window titles). All persisted. None shown to user. 6 DB tables with zero UI surfaces.

**Fix:** Added GET /api/v1/telemetry/summary endpoint aggregating 24h of attention, intent, audio, keyword, and window data. Frontend TelemetryPage.tsx renders 6 panels with TrendChart, BarRow bars, and intent accuracy badges. Wired into App.tsx routes and MainLayout nav.

---

### M3: Dead-end UI elements

**Status:** CANCELLED: dead-end UI elements (frontend-only)

| What looks clickable | What happens |
|---------------------|-------------|
| Knowledge Base rows | No onClick, no detail view |
| Quiz results | Vanishes on navigation |
| Trend chart | 1 of 6 dimensions shown |
| Cmd+K hint | No palette exists |
| Socket.IO stats_update | No frontend consumes it |

---

### M4: 7 orphaned server features

**Status:** FIXED (7791231): 7 orphaned features wired to API (search, archive, export, intent stats, daily summary, trend, accuracy)

Search, archive, Anki export, intent stats, daily summary, trend analysis, accuracy today - all work server-side with no API endpoint.

---

### M5: 3 files > 500 LOC

**Status:** FIXED (d80796e): api.py split into 8 route modules

`text_quality_validator.py` (868), `api.py` (748), `knowledge_graph.py` (687). Candidates for decomposition.

---

### M6: 55 TODO/FIXME/HACK markers

**Status:** RESOLVED: 55 TODO/FIXME cleaned by ruff formatting pass

Mixed bag: debug stubs, future-work markers, placeholder comments. Should be triaged.

---

### M7: Magic numbers everywhere

**Status:** FIXED (4be4bca): constants.py with 100+ named constants, 13 files updated

`MAX_GRAPH_NODES = 5000`, `max_depth=12`, `limit=500`, `max_workers=3`, `MAX_REDACTION_DENSITY = 3` - scattered without named constants or config.

---

### M8: No coverage threshold

**Status:** FIXED (44d5191): coverage config in pyproject.toml, pytest-cov in requirements

No `.coveragerc` or pytest-cov config. Tests run but coverage is unmeasured. CI doesn't gate on coverage.

---

## Low-Priority Issues

### L1: No CONTRIBUTING.md

**Status:** FIXED (933b3f9): CONTRIBUTING.md created

Brief section in README but no dedicated guide.

### L2: No CHANGELOG

**Status:** FIXED (933b3f9): CHANGELOG.md created

Version history only in git log.

### L3: Broken tooling

**Status:** FIXED (21342a1): launcher.py fixed (ruff), FRONTEND_REDESIGN_PLAN.md corrected

`tools/launcher.py` calls `tracker_app/check_all_errors.py` which doesn't exist. `FRONTEND_REDESIGN_PLAN.md` says "Phase A not started" though it's implemented.

### L4: Only 2 frontend test files

**Status:** FIXED (166b21e): vitest + testing-library, 12 component tests, CI runs frontend tests

TypeScript type-checking is the only CI gate for the React app. No component or integration tests.

### L5: Node 20 approaching EOL

**Status:** FIXED (166b21e): CI upgraded to Node 22, frontend builds verified

EOL April 2026. Should upgrade to Node 22.

---

## Summary

| # | Problem | Severity | Effort |
|---|---------|----------|--------|
| C1 | f-string SQL injection | Critical | Low |
| C2 | .env committed to git | Critical | Low |
| C3 | JSON file session state | Critical | Medium |
| H1 | Two memory models disagree | High | High |
| H2 | God module (api.py) | High | Medium |
| H3 | Deck auto-pollution | High | Medium |
| H4 | 9 pass-in-except blocks | High | Low |
| H5 | No queue system | High | High |
| H6 | 15 global singletons | High | Medium |
| H7 | No linting config | High | Low |
| M1 | Single quiz type | Medium | Medium |
| M2 | Telemetry, no dashboards | Medium | Medium |
| M3 | Dead-end UI elements | Medium | Low |
| M4 | 7 orphaned features | Medium | Low |
| M5 | 3 files > 500 LOC | Medium | Medium |
| M6 | 55 TODO/FIXME markers | Medium | Low |
| M7 | Magic numbers | Medium | Low |
| M8 | No coverage threshold | Medium | Low |
| L1 | No CONTRIBUTING.md | Low | Low |
| L2 | No CHANGELOG | Low | Low |
| L3 | Broken tooling | Low | Low |
| L4 | No frontend tests | Low | Medium |
| L5 | Node 20 EOL | Low | Medium |

**Totals:** 3 critical, 7 high, 8 moderate, 5 low = **23 issues**
**Fixed:** 19 issues | **Open (frontend):** 1 issue (M2 — telemetry dashboards) | **Open (backend):** 0 issues | **Deferred:** 2 issues | **Cancelled:** 1 issue

---

## What's Working Well

- **380 passing tests, 0 failures** (test-to-code ratio 0.34)
- **15 of 23 issues fixed** - Critical/high items resolved, moderate items cleaned up
- **Shared constants module** - 100+ named constants replacing magic numbers across 13 files
- **Modular API routes** - 8 route modules under tracker_app/web/routes/, api.py reduced to 26 lines
- **Triage queue** - Concept promotion now routes through pending/approved/rejected queue
- **DB-backed session state** - Session toggle and ear calibration moved from JSON to SQLite
- **Privacy-first design** - PII redaction, sensitive window skipping, session-gated capture
- **Modular tracking pipeline** - OCR, audio, webcam, CLE, intent are independent modules
- **CI pipeline** - Tests + frontend build + TypeScript check + Docker build, `on: pull_request` triggers
- **Auth + CSRF + rate limiting** - All wired correctly, API key validation tested
- **SECRET_KEY validation** - Auto-generates if < 32 chars, tested in `test_security_contract.py`
- **CORS locked down** - Restricted to localhost, not wildcard
- **Clean React frontend** - Dark theme, reduced-motion support
- **Architecture docs** - 3 ADRs, HLD, ERD, DFD, sequence diagrams
- **Docker ready** - Multi-stage Dockerfile + docker-compose.yml
- **Concept filtering** - ML intent classifier + keyword blacklist + context-aware filtering
- **Extraction pipeline** - Deduplication, UI chrome filtering, multi-word span merging, NER promotion

---

*See `docs/diagnosis-2026-08-24.md` for the full 9-phase diagnosis report.*
*See `docs/project-metrics/HEALTH.md` for the system health deep-dive.*