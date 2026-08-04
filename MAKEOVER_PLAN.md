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

- [ ] **True clean-room test.** ⏸️ **ON HOLD** — Move the current `venv` aside, create a fresh one, run `pip install -r requirements.txt` and `npm install` with nothing else present, then try to start `main.py` and `web/app.py`. This is the only way to know the install path actually works — it's how the `sounddevice`/`librosa` gap was found. Note: the `venv_cleanroom/` directory in the repo is a stale pre-React demo env (missing Flask, mediapipe, librosa, transformers, spacy) and does NOT count as this test.
- [x] **Full import audit.** AST-scanned every top-level `import`/`from` under `tracking/`, `learning/`, `db/`, and `web/` and diffed against `requirements.txt`. All third-party imports now covered: added `numpy`, `networkx` (knowledge_graph), `psutil` (loop), `pywin32>=305` with a `platform_system == "Windows"` marker (win32gui). `dlib` (legacy `face_detection_module.py`, superseded by webcam_module) is now import-guarded so the module stays importable without dlib. No second hidden gap like the `sounddevice`/`librosa` one was found.
- [ ] **Live end-to-end run, not just seeded data.** `tools/populate.py` proves the dashboard can render data; it doesn't prove the tracker produces good data. Run `main.py` through a real 15–20 minute study session and confirm concepts actually flow OCR → knowledge graph → Graph page, and that a quiz eventually surfaces for something tracked during that session.
- [x] **Check the browser-extension / `/ingest` path.** `/api/v1/ingest` in `web/api.py` works and is now covered by tests (`test_api.py::TestAPIBrowserIngest` — concepts saved, short text skipped, missing text 400s). No extension exists, but the README only lists it as **Planned** (Phase 10), so no false claim to remove.
- [ ] **Security checklist from `DEPLOYMENT.md`** (`SECRET_KEY`, `DEBUG=False`, etc.) — only blocking if this will be deployed or demoed somewhere public; not needed for local-only use.
- [x] **README quickstart walkthrough.** Followed it literally against the code. Fixes made: the Manual Start section claimed `python -m tracker_app.main` "spawns both web dashboard and background tracker" — it only runs the background tracker; dashboard is `python -m tracker_app.web.app`. Replaced both references to the non-existent `FKT_IMPLEMENTATION_PLAN.md` with `MAKEOVER_PLAN.md`/`architecture/`. Updated the stale Roadmap table (Phases 3–9 and 11 were already done; only Phase 10 Browser Ext is still planned).

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

**Status: Phases 0–5 built, Phase 6 verification in progress**
