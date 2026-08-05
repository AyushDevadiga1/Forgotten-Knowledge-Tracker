# FKT Makeover Plan

**Goal:** Take FKT from "impressive code that doesn't fully run" to a working, demoable system with a frontend that actually surfaces what the backend already does.

**Status snapshot as of Aug 2, 2026** — Phases 0–5 are implemented and look right on inspection, but haven't all been proven against a true clean-room install. One real gap was already caught this way: `requirements.txt` was missing `sounddevice`/`librosa`, which `audio_module.py` imports directly. That specific gap is now fixed (both added to `requirements.txt` under a new "Audio Processing" section) — but it was only found by inspection, not by an actual fresh install, so it hasn't been proven to be the *only* one. Phase 6 below exists to run that real clean-room test and catch anything else like it before this gets marked done.

---

## Phase 0 — Get it running at all (blocking everything else)

- [x] **Restore `tracker_app/learning/concept_scheduler.py`.** Restored from git history (`f1ccec8`). Import chain resolved across `activity_monitor.py`, `quiz_engine.py`, and `web/api.py`.
- [x] **Clean-room startup test.** Migrations run via `python -m tracker_app.db.migrations`, `tracker_app.main` boots without errors, `tracker_app.web.app` starts cleanly, API endpoints verified.
- [x] **Resolve the duplicate OpenCV install.** Removed `opencv-python` from `requirements.txt` (keeping `opencv-contrib-python` superset).
- [x] **Verify `TESSERACT_PATH` / OCR actually resolves.** Added startup sanity-check warning in `ocr_module.py` if binary is missing.

---

## Phase 1 — Dependency & environment cleanup

- [x] Removed unused heavy packages (`paddleocr`, `streamlit`, `streamlit-autorefresh`) from `requirements.txt`.
- [x] Removed commented-out `dlib` references.
- [x] Re-pinned version bounds in `requirements.txt`.
- [x] Confirmed `Flask-WTF` stays in `requirements.txt`.
- [x] Verified setup instructions in `README.md` and `DEPLOYMENT.md`.

---

## Phase 2 — Data layer verification

- [x] Ran `tracker_app/tools/populate.py` against DB, seeded 54 concepts, 100 sessions, and 200 logs.
- [x] Cross-checked caller methods in `learning_tracker.py` and `activity_monitor.py` against `db/repository.py`.
- [x] Applied and verified idempotency of all 6 migrations in `db/migrations.py`.

---

## Phase 3 — Frontend: build it out to match the backend

- [x] `npm install` executed in `tracker_app/web/frontend` (174 packages installed).
- [x] **Graph page** — Built `GraphPage.tsx` fetching `/graph/stats` and `/graph/gaps` with force bubble map, stats tiles, and knowledge gap cards.
- [x] **Quiz page** — Built `QuizPage.tsx` fetching `/quiz/current` and submitting answers to `/quiz/answer` tied to SM-2.
- [x] **Intent feedback loop** — Verified `IntentFeedbackToast.tsx` mounted in `MainLayout.tsx`.
- [x] **Nav/layout pass** — Added Graph (`Share2`) and Quiz (`Zap`) routes and navigation entries in `MainLayout.tsx` and `App.tsx`.
- [x] **Empty/loading/error states** — Implemented empty and backend-down fallback components across pages.

---

## Phase 4 — Testing & CI

- [x] Moved non-test scripts (`test_db.py`, `test_memory_graph.py`, `test_audio.py`) out of `tracker_app/tests/` to `scripts/debug/`.
- [x] Ran `pytest tracker_app/tests/` — **74/74 tests passed**.
- [x] Created GitHub Actions CI workflow in `.github/workflows/ci.yml`.

---

## Phase 5 — Documentation reconciliation

- [x] Created `ADR-003-Reinstate-RandomForest-Intent.md` superseding ADR-002 for Intent Classification.
- [x] Updated `architecture/high_level/tech_stack.md` and `hld.md` to reflect MediaPipe and React/TypeScript stack.
- [x] Consolidated `documentation/` folder: archived 14 duplicate files to `documentation/archive/`.
- [x] Renamed raw output screenshots in `outputs/` to descriptive names and added `outputs/README.md` catalog.

---

## Phase 6 — Verification & completion

Everything above was checked off against a `venv` that's already fully populated — that's not the same as proof it works from scratch. This phase is about verifying, not building.

- [x] **True clean-room test.** Fresh `venv` created from scratch, `pip install -r requirements.txt` installed everything with zero manual fixes (the old `venv` was moved aside and has since been deleted — only the clean-room env remains). `npm ci` + `npm run build` also succeeded from a clean tree. Then `main.py` and `web/app.py` were both started and verified against the fresh env (below). One gap this caught: `pytest` was not in `requirements.txt`, so a fresh install couldn't run the test suite — added it under a "Testing" section. (The stale `venv_cleanroom/` directory was deleted during cleanup.)
- [x] **Full import audit.** AST-scanned every top-level `import`/`from` under `tracking/`, `learning/`, `db/`, and `web/` and diffed against `requirements.txt`. All third-party imports now covered: added `numpy`, `networkx` (knowledge_graph), `psutil` (loop), `pywin32>=305` with a `platform_system == "Windows"` marker (win32gui). `dlib` (legacy `face_detection_module.py`, superseded by webcam_module) is now import-guarded so the module stays importable without dlib. No second hidden gap like the `sounddevice`/`librosa` one was found. (Phase 8 follow-up: `face_detection_module.py` plus the never-referenced `TEXT_QUALITY_USAGE_EXAMPLES.py`, `enhanced_review_interface.py`, `simple_review_interface.py`, and empty `models/__init__.py` were moved to the git-ignored `legacy/` folder — dead code stays on disk but is out of the repo.)
- [x] **Live end-to-end run.** Started `main.py` (via new `ALLOW_WEBCAM=false` non-interactive path) and confirmed real OCR → keyword extraction → concept scheduler → DB flow (`source='ocr'` encounters + intent predictions written). Also verified `/api/v1/ingest` live (15 concepts saved from a study passage), and — after fixing a real bug — `/api/v1/graph/stats` returned 153 concept nodes, `/api/v1/quiz/current` returned a generated quiz, and `/api/v1/graph/gaps` returned 5 knowledge gaps. **Bug fixed:** the knowledge graph is process-local and was never synced from the DB, so the dashboard's Graph page/quiz were empty on a fresh web-app start (`KNOWLEDGE_GRAPH_PATH` in config was dead). Added a lazy `_ensure_graph_loaded()` in `knowledge_graph.py` that syncs `tracked_concepts` → graph on first use. A full 15–20 minute study session with real study content on screen remains the ideal final confirmation.
- [x] **Check the browser-extension / `/ingest` path.** `/api/v1/ingest` in `web/api.py` works and is now covered by tests (`test_api.py::TestAPIBrowserIngest` — concepts saved, short text skipped, missing text 400s). No extension exists, but the README only lists it as **Planned** (Phase 10), so no false claim to remove.
- [x] **Security checklist from `DEPLOYMENT.md`.** N/A for local-only use, so nothing blocking. Verified: no `.env`/secrets tracked in git, `SECRET_KEY` falls back to a dev value, `DEBUG` defaults to `False`, and API-key auth middleware exists (`web/auth.py`, default-off via `NO_AUTH`). Production notes added to `DEPLOYMENT.md` (set `SECRET_KEY`, `DEBUG=False`, `API_KEY` + `NO_AUTH=false`, use gunicorn).
- [x] **README quickstart walkthrough.** Followed it literally against the code. Fixes made: the Manual Start section claimed `python -m tracker_app.main` "spawns both web dashboard and background tracker" — it only runs the background tracker; dashboard is `python -m tracker_app.web.app`. Replaced both references to the non-existent `FKT_IMPLEMENTATION_PLAN.md` with `MAKEOVER_PLAN.md`/`architecture/`. Updated the stale Roadmap table (Phases 3–9 and 11 were already done; only Phase 10 Browser Ext is still planned). `README` also claims `ALLOW_WEBCAM` in `.env` skips the webcam prompt — made that true in `main.py` (it used to always prompt).

Also caught while verifying: the CI frontend typecheck was broken — `typescript` was missing from `frontend/package.json` devDependencies, so `npx tsc --noEmit` silently resolved to the deprecated `tsc@2.0.4` shim and failed. Added `typescript@^5.9.3`; `npx tsc --noEmit` now passes. Test count is now **77** (74 + 3 new `/ingest` tests).

---

## Definition of done

A grader, recruiter, or future-you should be able to:
1. Clone the repo fresh.
2. Run `pip install -r requirements.txt` and `npm install` with zero manual fixes.
3. Run migrations, start `main.py` and `web/app.py`, start the frontend dev server.
4. See live data flow from screen/audio capture → knowledge graph → dashboard, including the Graph and Quiz pages.
5. Run `pytest tracker_app/tests/` and see it pass, with no fake "tests" in the mix.
6. Read the README/ADRs and find them consistent with what the code actually does.

**Status: Phase 6 complete (clean-room, import audit, E2E, /ingest, security, README all verified).**

---

## Phase 7 — Post-verification improvements

Three fixes/features flagged after Phase 6's live E2E run, in ascending order.

- [x] **OCR noise cleanup.** The live E2E run captured random on-screen window text, and word fragments like `ano`, `ity`, `heh`, `bene`, `tae` (all OCR artifacts) were being persisted as tracked concepts. Added `is_plausible_concept()` in `learning/text_quality_validator.py` and applied it inside `ConceptScheduler.add_concept()` — the single choke point used by both the OCR tracking loop and `/api/v1/ingest`. It rejects fragments, vowel-less garbage (`hty`), doubled-run noise (`aannup`), and common suffix fragments (`tion`, `ation`), while keeping real keywords, multi-word phrases, and ALL-CAPS acronyms. `add_concept()` now returns `None` for rejected concepts so callers only count/track genuinely saved ones. (4 new tests.)
- [x] **Knowledge-graph persistence.** The in-memory `networkx` graph was rebuilt from the DB on every web-app start, re-embedding all concepts with SentenceTransformer each time. It now persists to `KNOWLEDGE_GRAPH_PATH` (`tracker_app/data/knowledge_graph.pkl`, previously dead config). `_ensure_graph_loaded()` loads the pkl on first use and reconciles only concepts the DB gained since the last save; `sync_db_to_graph()` is incremental and persists via an atomic tmp-file replace. The pkl is a cache, not the source of truth — a missing/corrupt file falls back to a full DB rebuild. (4 new tests.)
- [x] **Chrome extension (FKT Capture).** New `tracker_app/web/extension/` (MV3: manifest + background service worker + content script + popup). Select text in any tab, click the popup button, and it POSTs to the local `/api/v1/ingest`; the fetch runs from the background worker with `host_permissions`, so no page CORS is involved. The dashboard's `web/app.py` CORS config now also allows `chrome-extension://*` origins for defense in depth (verified: `Access-Control-Allow-Origin` echoes the extension origin and the passage is saved). README's Phase 10 row flipped to **Done**.

**Status: Phase 7 complete. Full suite: 85 tests passing.**

---

## Phase 8 — Dead-code removal & comment pruning

AST-based dead-code audit (cross-module import map + per-name call-graph) plus removal of redundant changelog comments, for peer-review readability.

- [x] **Dead modules relocated to git-ignored `legacy/`.** `scripts/TEXT_QUALITY_USAGE_EXAMPLES.py`, `tools/enhanced_review_interface.py`, `tools/simple_review_interface.py` (all three had broken `from core.*` imports and zero references), the empty `models/__init__.py`, and the legacy `tracking/face_detection_module.py` were moved to `legacy/` (git-ignored) instead of deleted — preserved on disk, out of the repo.
- [x] **Dead functions removed** (each confirmed to have zero callers across app code, tests, and CLI entry points): `db_module.get_db_connection` + the three `pass` stubs (`init_multi_modal_db`, `init_memory_decay_db`, `init_metrics_db`); `memory_model.compute_memory_score` (pre-AWFC legacy) and `log_forgetting_curve` (only writer to the legacy `memory_decay` table); `sm2_memory_model.estimate_learning_curve` and `format_retention_percentage`; `keyword_extractor.extract_keywords_batch` + the unused `LightweightKeywordExtractor` alias; `activity_monitor.log_feedback`, `get_concept_recommendations`, `ThreadSafeCounter.get_value`; `realtime.broadcast_tracker_status`/`broadcast_concept_discovered`/`broadcast_review_completed`/`background_stats_updater` (only `broadcast_micro_quiz` is used, by `loop.py`); `knowledge_graph.add_edges`; `repository.delete_item`. Unused imports (`sqlite3`, `contextmanager`, `DB_PATH`, `DATETIME_FORMAT`, `List`) pruned alongside.
- [x] **Redundant comments pruned.** `# FKT 2.0 Phase N` / `# Fixes:` / `# Changes from v1:` changelog headers in ~20 modules replaced with concise module docstrings (AWFC formula, CLe signal list, and intent feature vector kept as documentation). Moji­bake section markers (`Phase 6:`/`Phase 8:`/`Phase 7:`) in `knowledge_graph.py`, `loop.py`, `api.py`, `models.py`, and `ocr_module.py` cleaned. Kept meaningful inline comments (e.g. `# FKT 2.0 fix: read actual tracked concepts, not OS window titles`).

**Status: Phase 8 complete. Full suite: 85 tests passing.**
