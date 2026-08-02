# FKT Makeover Plan

**Goal:** Take FKT from "impressive code that doesn't fully run" to a working, demoable system with a frontend that actually surfaces what the backend already does.

**Status snapshot as of Aug 2, 2026** — ALL PHASES COMPLETE. The system is fully operational, tests pass (74/74), database migrations are applied, repository pattern is fully integrated, knowledge graph & quiz frontend pages are live, CI workflow is set up, and documentation is reconciled.

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

## Definition of done

A grader, recruiter, or future-you should be able to:
1. Clone the repo fresh.
2. Run `pip install -r requirements.txt` and `npm install` with zero manual fixes.
3. Run migrations, start `main.py` and `web/app.py`, start the frontend dev server.
4. See live data flow from screen/audio capture → knowledge graph → dashboard, including the Graph and Quiz pages.
5. Run `pytest tracker_app/tests/` and see it pass, with no fake "tests" in the mix.
6. Read the README/ADRs and find them consistent with what the code actually does.

**Status: COMPLETED**
