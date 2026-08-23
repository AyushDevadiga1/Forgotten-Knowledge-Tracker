# Current Problems - FKT

> Last updated: 2026-08-24
> Sources: `docs/project-metrics/HEALTH.md`, `docs/diagnosis-2026-08-24.md` (9-phase repo scan)

---

## Critical Issues

### C1: f-string SQL injection in migrations.py

**File:** `tracker_app/db/migrations.py:197, 226`

`cursor.execute(f"PRAGMA table_info({table})")` and `f"SELECT {col} FROM {table}"` use f-string interpolation with table/column names. Currently safe (internal schema inspection only), but the pattern is a ticking bomb for any future caller passing user input.

**Fix:** Parameterized queries or column-name allowlist.

---

### C2: .env file committed to git

**File:** Root `.env`

The `.env` file with `SECRET_KEY=test-secret-key` is tracked in version control. `.gitignore` has `.env` but the file was committed before the rule existed.

**Fix:** Remove from git history, rotate the key.

---

### C3: Session state via JSON file + FileLock

**File:** `tracker_app/tracking/session_state.py`

Shares mutable state between tracker and web server via JSON file + FileLock. Under concurrent access (Docker, multiple workers), this is a race condition. The `_graph_lock` threading lock in `knowledge_graph.py` adds a second locking mechanism for the same conceptual state.

**Fix:** Replace with proper IPC or database-backed state.

---

## High-Priority Issues

### H1: Two memory systems that disagree

The deck (`LearningItem` + SM-2) and concept graph (`TrackedConcept` + AWFC) sync one-way: concepts promote to deck, but deck performance never feeds back. User sees conflicting "what you know" signals.

**Status:** Identified in HEALTH.md Problem 1. No fix started.

---

### H2: God module - web/api.py

748 LOC, 27 routes. Mixes auth, CRUD, stats, graph, quiz, ingest, and session control. Every feature addition touches this file.

**Fix:** Split into Flask blueprints (auth, items, quiz, graph, session).

---

### H3: Deck auto-pollution

`concept_promotion.py` auto-promotes keywords with placeholder answers. No triage queue. Keywords flood the deck unchecked.

**Status:** Identified in HEALTH.md Problem 2. No fix started.

---

### H4: 9 pass-in-except blocks

Silent exception swallowing hides failures. These should either log the error or re-raise.

**Fix:** Add logging or re-raise in each block.

---

### H5: No queue system

ML inference (spaCy NER, sentence-transformers, intent classification) and OCR run inline in the tracking loop via `ThreadPoolExecutor(max_workers=3)`. No async offload. When the loop backs up, everything stalls.

**Fix:** Add Celery/RQ for ML inference, or at minimum make extraction async.

---

### H6: 15 global singletons

`global` used across 15 locations for lazy-loaded instances (`_cle_instance`, `_extractor_instance`, `_model_data`, `_engine`, `_SessionLocal`, etc.). Hidden coupling, hard to test.

**Fix:** Replace with dependency injection or a proper IoC container.

---

### H7: No linting or formatting config

No `.flake8`, `ruff.toml`, `mypy.ini`, `.eslintrc`, or `.prettierrc`. Code style enforced only by convention.

**Fix:** Add `ruff` to Python, `eslint` + `prettier` to frontend. Wire to CI.

---

## Moderate Issues

### M1: Single quiz question type

`quiz_engine.py` generates exactly one shape: "Which of these concepts have you been studying?" No cloze, no typed recall, no fill-in-the-blank.

**Status:** Identified in HEALTH.md Problem 3. No fix started.

---

### M2: Rich telemetry, zero dashboards

6 signals collected (OCR, audio, webcam attention, CLE, intent, window titles). All persisted. None shown to user. 6 DB tables with zero UI surfaces.

**Status:** Identified in HEALTH.md Problem 4. No fix started.

---

### M3: Dead-end UI elements

| What looks clickable | What happens |
|---------------------|-------------|
| Knowledge Base rows | No onClick, no detail view |
| Quiz results | Vanishes on navigation |
| Trend chart | 1 of 6 dimensions shown |
| Cmd+K hint | No palette exists |
| Socket.IO stats_update | No frontend consumes it |

---

### M4: 7 orphaned server features

Search, archive, Anki export, intent stats, daily summary, trend analysis, accuracy today - all work server-side with no API endpoint.

---

### M5: 3 files > 500 LOC

`text_quality_validator.py` (868), `api.py` (748), `knowledge_graph.py` (687). Candidates for decomposition.

---

### M6: 55 TODO/FIXME/HACK markers

Mixed bag: debug stubs, future-work markers, placeholder comments. Should be triaged.

---

### M7: Magic numbers everywhere

`MAX_GRAPH_NODES = 5000`, `max_depth=12`, `limit=500`, `max_workers=3`, `MAX_REDACTION_DENSITY = 3` - scattered without named constants or config.

---

### M8: No coverage threshold

No `.coveragerc` or pytest-cov config. Tests run but coverage is unmeasured. CI doesn't gate on coverage.

---

## Low-Priority Issues

### L1: No CONTRIBUTING.md

Brief section in README but no dedicated guide.

### L2: No CHANGELOG

Version history only in git log.

### L3: Broken tooling

`tools/launcher.py` calls `tracker_app/check_all_errors.py` which doesn't exist. `FRONTEND_REDESIGN_PLAN.md` says "Phase A not started" though it's implemented.

### L4: Only 2 frontend test files

TypeScript type-checking is the only CI gate for the React app. No component or integration tests.

### L5: Node 20 approaching EOL

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

---

## What's Working Well

- **378 passing tests, 0 failures** (test-to-code ratio 0.33)
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