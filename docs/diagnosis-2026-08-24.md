# Repository Diagnosis: Forgotten Knowledge Tracker (FKT)

> Generated: 2026-08-24 | Skill: repo-diagnosis (9-phase scan)

## 0. Snapshot
- **Language(s):** Python 3.11 (backend), TypeScript/React (frontend)
- **Framework(s):** Flask 3.1 + SQLAlchemy 2.0 + Flask-SocketIO (backend), React + Vite + Tailwind (frontend)
- **Scale:** ~91 Python files, ~14,768 LOC; ~41 TS/JS files, ~3,410 LOC; 42 test files, ~4,885 LOC
- **Type:** Desktop learning tracker with OCR/audio/webcam capture loop, ML intent classification, spaced repetition, knowledge graph, web dashboard
- **Dependencies:** 26 Python packages, ~15 npm packages
- **Diagnosis scope:** phases 0-9 completed

---

## 1. Critical Issues

**[SECURITY] f-string SQL injection in migration tool** - `tracker_app/db/migrations.py:197`
`cursor.execute(f"PRAGMA table_info({table})")` and `f"SELECT {col} FROM {table}"` at line 226 use f-string interpolation with table/column names. While these come from internal schema inspection (not user input), the pattern is dangerous - any future caller passing user-controlled table names creates an injection vector. Parameterized queries or allowlists should be used.

**[SECURITY] .env file committed to git** - Root `.env` file is tracked in version control. Even with a `SECRET_KEY=test-secret-key` placeholder, this file should never be committed. The `.gitignore` has `.env` but the file was committed before the rule existed.

**[RELIABILITY] Session state via JSON file + FileLock** - `session_state.py` shares mutable state between the tracker process and the Flask web server via a JSON file with `FileLock`. Under concurrent access (e.g., Docker + multiple workers), this is a race condition risk. The `_graph_lock` threading lock in `knowledge_graph.py` compounds this - two different locking mechanisms for the same conceptual state.

---

## 2. High-Priority Concerns

**[ARCHITECTURE] Two disconnected memory systems** - The deck brain (`LearningItem` + SM-2) and concept brain (`TrackedConcept` + AWFC) sync one-way: concepts promote to deck, but deck performance never feeds back. User sees conflicting "what you know" signals.

**[ARCHITECTURE] God module: `web/api.py`** - 748 LOC, 27 routes. Mixes auth, CRUD, stats, graph, quiz, ingest, and session control in a single file. Every feature addition touches this file.

**[QUALITY] 9 pass-in-except blocks** - Silent exception swallowing hides failures. These should either log the error or re-raise.

**[SCALABILITY] No queue system** - ML inference (spaCy NER, sentence-transformers embedding, intent classification) and OCR run inline in the tracking loop. No async offload (Celery, RQ, etc.). When the loop backs up, everything stalls.

**[QUALITY] 15 global singletons** - `global` used across 15 locations for lazy-loaded instances (`_cle_instance`, `_extractor_instance`, `_model_data`, `_ENGLISH_WORDS`, `_engine`, `_SessionLocal`, etc.). Makes testing harder and creates hidden coupling.

**[QUALITY] No linting or formatting config** - No `.flake8`, `ruff.toml`, `mypy.ini`, `.eslintrc`, or `.prettierrc`. Code style is enforced only by convention.

---

## 3. Moderate Issues

**[MAINTAINABILITY] No CONTRIBUTING.md** - README has a brief contributing section but no dedicated guide.

**[MAINTAINABILITY] No CHANGELOG** - Version history is only in git log.

**[QUALITY] No coverage threshold** - No `.coveragerc` or pytest-cov config. Tests run but coverage is unmeasured.

**[CODE HEALTH] 3 files > 500 LOC** - `text_quality_validator.py` (868), `api.py` (748), `knowledge_graph.py` (687). Candidates for decomposition.

**[CODE HEALTH] 55 TODO/FIXME/HACK markers** - Some are debug logging stubs, some are genuine future-work markers. Should be triaged.

**[CODE HEALTH] Magic numbers** - `MAX_GRAPH_NODES = 5000`, `max_depth=12`, `limit=500`, `max_workers=3`, `MAX_REDACTION_DENSITY = 3` scattered across files without named constants or config.

**[FRONTEND] Only 2 frontend test files** - TypeScript type-checking (`tsc --noEmit`) is the only CI gate for the React app. No component or integration tests.

**[FRONTEND] Dead UI elements** - KB rows have `cursor-pointer` but no onClick. Quiz results vanish on navigation. Cmd+K hint with no palette.

**[SERVER] 7 features orphaned** - Search, archive, Anki export, intent stats, daily summary, trend analysis, accuracy today - all exist server-side with no API endpoint.

---

## 4. Observations and Positives

- **Privacy-first design** - PII redaction, sensitive window skipping, session-gated capture. Excellent data hygiene.
- **Modular tracking pipeline** - OCR, audio, webcam, CLE, intent are independent modules with clean interfaces.
- **378 passing tests, 0 failures** - Strong test-to-code ratio (0.33). Tests cover edge cases (rate limiting, security contracts, graph sync, concept promotion).
- **CI pipeline is solid** - Tests + frontend build + TypeScript check + Docker build. `on: pull_request` triggers.
- **Auth + CSRF + rate limiting** - All wired correctly. API key validation, Flask-WTF CSRF, flask-limiter.
- **SECRET_KEY validation** - Config auto-generates if too short (< 32 chars). Tested in `test_security_contract.py`.
- **CORS locked down** - Not wildcard. Restricted to localhost origins in both Flask and SocketIO.
- **Clean React frontend** - Dark theme, reduced-motion support, consistent component library.
- **Architecture documentation exists** - 3 ADRs, high-level HLD, system architecture, tech stack, ERD, DFD, sequence diagrams.
- **Docker ready** - Multi-stage Dockerfile + docker-compose.yml.

---

## 5. Bottleneck Map

The critical path is: **tracking loop (5s) -> OCR (20s) -> spaCy NER + YAKE extraction -> knowledge graph update -> concept scheduler -> deck promotion**. This entire pipeline runs synchronously in a `ThreadPoolExecutor(max_workers=3)`. The spaCy `en_core_web_sm` model load and `sentence-transformers` embedding are the heaviest operations. Under sustained use, the 3-thread pool will saturate: OCR capture, audio classification, and NER extraction compete for the same threads. The JSON-file session state adds I/O contention on top. When the loop backs up, intent classification (RandomForest predict) and webcam face detection (MediaPipe) queue behind the NER bottleneck.

---

## 6. Deprecation Timeline

| Package / Runtime | Pinned version | EOL date | Risk |
|-------------------|---------------|----------|------|
| Python | >=3.11 | Oct 2027 | Low (within support) |
| Node.js (CI) | 20 | April 2026 | **Approaching EOL** |
| spaCy en_core_web_sm | 3.8.0 | -- | Low |
| opencv-contrib-python | >=4.9.0 | -- | Low |
| mediapipe | >=0.10.14 | -- | Low (Google actively maintains) |

Node 20 reaches EOL in April 2026 - 8 months away. Should plan upgrade to Node 22.

---

## 7. CI/CD Gap Summary

The pipeline runs pytest (backend) + `tsc --noEmit` + `npm run build` (frontend) on push to main/dev and on PRs. **What it does NOT gate:** no lint step (no flake8/ruff/mypy), no coverage threshold, no frontend tests (only type-check + build), no security scanning (no bandit/safety), no dependency audit, no Docker image scanning. A PR that adds a bare `except: pass` or introduces a type error in a non-imported path would merge without detection. The `.env` in CI uses `SECRET_KEY=test-secret-key` (15 chars) which is below the 32-char validation threshold - this works because `config.py` auto-generates, but it masks the real production risk.

---

## 8. Scalability Ceiling

The first architectural constraint is **the synchronous tracking loop with 3-thread pool**. When traffic doubles (longer study sessions, more captured concepts, larger knowledge graph), the loop's cycle time will increase because:
1. spaCy NER scales linearly with text length
2. Knowledge graph operations (`ensure_graph_loaded`, `reconcile_concepts`) acquire `_graph_lock` and block the entire loop
3. JSON-file session state serializes all state mutations through FileLock
4. No caching layer - every query hits SQLite directly

The system is designed for single-user desktop use. Scaling to multi-user (e.g., a shared deployment) would require: (a) replacing JSON state with proper IPC/database, (b) adding a task queue for ML inference, (c) implementing connection pooling for SQLite or migrating to PostgreSQL.

---

## 9. Recommended Priority Order

1. **Remove .env from git history** - Security hygiene. Add to `.gitignore` properly and rotate the committed secret key.
2. **Fix f-string SQL in migrations.py** - Replace with parameterized queries or allowlist. Small change, big risk reduction.
3. **Split `api.py` into blueprints** - Extract auth, items, quiz, graph, session into separate blueprint modules. Unblocks parallel development.
4. **Add linting (ruff) to CI** - Catches bare excepts, unused imports, style violations automatically. Low effort, high ROI.
5. **Wire orphaned server features to API** - 7 features already work server-side. Adding API endpoints is mechanical. Immediate user value.
6. **Add a triage queue** - Show captured concepts before they auto-promote to the deck. Prevents deck pollution.
7. **Plan Node 20 -> 22 upgrade** - EOL in April 2026. Do it before it becomes urgent.

---

> _Diagnosis complete. All 9 phases run. 3 critical, 6 high-priority, 8 moderate issues found._