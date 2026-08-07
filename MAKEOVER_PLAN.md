# FKT Makeover Plan

**Goal:** Take FKT from "impressive code that doesn't fully run" to a working, demoable system with a frontend that actually surfaces what the backend already does — and that behaves the way a human actually using it would want it to.

**Status as of this rewrite:** Phases 0–9 are done and verified (the system runs, is tested, has a working frontend, and correctly gates concept capture to explicit study sessions). This rewrite exists because a deeper look at the frontend and the two "interrupt" mechanisms (intent-feedback toast, micro-quiz push) found the human-facing layer is untuned to the point of actively working against the app's own purpose. **Phase 10 below is the current priority** — everything else is real, working infrastructure that this phase needs to actually put to good use.

---

## Resolved (Phases 0–9) — condensed record

**Phase 0 — Runtime restored.** `concept_scheduler.py` recovered from git history; `db/repository.py` rebuilt (`LearningRepository`/`TrackingRepository` were missing entirely, blocking both `main.py` and `web/app.py` from starting). OpenCV duplicate install resolved; Tesseract path now checked at startup instead of failing silently.

**Phase 1 — Dependencies cleaned.** Removed `paddleocr`, `streamlit`, `streamlit-autorefresh`, and a dead commented-out `dlib` line from `requirements.txt`. A later fresh-install test caught `sounddevice`/`librosa` missing (used directly by `audio_module.py`) — added back.

**Phase 2 — Data layer verified.** `tools/populate.py` seed run confirmed working; all 6 migrations confirmed idempotent; `db/repository.py` methods cross-checked against every caller in `learning_tracker.py` and `activity_monitor.py`.

**Phase 3 — Frontend parity built.** Graph page (`/graph/stats`, `/graph/gaps`) and Quiz page (`/quiz/current`, `/quiz/answer`) built and wired into `MainLayout` nav, with empty/loading/backend-down states.

**Phase 4 — Testing & CI.** Three files masquerading as tests (`test_db.py`, `test_memory_graph.py`, `test_audio.py` — none had real assertions, one triggered a live microphone recording on import) moved out of `tests/`. GitHub Actions CI added. Real test count grew from 74 to 85 through Phase 8.

**Phase 5 — Docs reconciled.** `ADR-003` supersedes `ADR-002`: the RandomForest intent classifier is kept, now justified by training on real user feedback (`FeedbackRepository`) rather than the synthetic data ADR-002 correctly criticized. `tech_stack.md` corrected (MediaPipe, not `dlib`). `documentation/` deduplicated into an `archive/`.

**Phase 6 — Clean-room verified.** A truly fresh `venv` + `npm install` confirmed the install path works with zero manual fixes; an import audit caught a few more gaps (`numpy`, `networkx`, `psutil`, `pywin32`); a live end-to-end run confirmed OCR → keyword extraction → concept scheduler → DB → dashboard actually flows.

**Phase 7 — Concept-quality & persistence fixes.** `is_plausible_concept()` added to reject OCR-artifact fragments (`"ano"`, `"hty"`) — this addresses *garbled* text, not *irrelevant* text; see Phase 10 for the latter. Knowledge graph now persists to `knowledge_graph.pkl` instead of rebuilding from scratch on every start. A Chrome extension (`FKT Capture`) was built for the `/ingest` path.

**Phase 8 — Dead code removed.** Legacy/broken modules moved to a git-ignored `legacy/` folder; ~15 confirmed-zero-caller functions removed; changelog-style comments replaced with real docstrings.

**Phase 9 — Session-gated capture (the core relevance fix).** `tracking/session_state.py` implements a file-based Start/Stop Study Session toggle shared between the web process and the tracker process. `track_loop()` now gates *all* capture — not just concept-saving, but OCR/audio/webcam themselves — behind `session_active`, and even within an active session only persists concepts on cycles the intent classifier labels as `studying` (`SESSION_ALLOWED_INTENTS` in `config.py`). Verified correct by reading `loop.py`, `session_state.py`, and `config.py` directly: this is real, and it's wired up properly.

---

## Phase 10 — Frontend & notification integrity (current priority)

Phase 9 fixed **what** gets captured. This phase exists because a fresh read of the frontend and both "interrupt" mechanisms — the intent-feedback toast and the micro-quiz push — found that neither is tuned for a human actually trying to study. Everything below was confirmed by reading the current code, not inferred from the architecture looking reasonable on paper.

<!--PHASE10_SLOT_1-->

- [x] **Feedback toast stops nagging.** `IntentFeedbackToast` polls `/intent/recent` every 10 s and shows a card whenever the latest `intent_predictions` row has `user_feedback IS NULL`. But the tracker writes a new prediction every 5 s during a session, so the toast is effectively always on screen — no cooldown, no dismissal, no "already shown" marker. Fix: add a nullable `prompted_at` column (migration 007, ADD COLUMN is auto-guarded); `/intent/recent` becomes "next promptable prediction" — it only returns a row that is (a) unanswered, (b) never shown before, (c) at least `TOAST_COOLDOWN_MINUTES` (5) after the previous prompt, and it stamps `prompted_at` when returned so the same row is never re-shown. Add a DISMISS (X) on the toast that hides it (the cooldown + `prompted_at` do the rest). Max realistic ask: once per 5 min, only about the newest prediction, never twice about the same one.
- [x] **Micro-quiz fires at a humane time and never stalls the loop.** `IDLE_CYCLES_REQUIRED = 3` means the quiz interrupt fires after ~15 s of idle — far too aggressive. Raise to 12 (~60 s), and gate `_maybe_trigger_quiz` behind the active study session so no quiz fires while the user isn't in a session at all. The bigger bug (found live): the trigger calls `get_graph()` synchronously in the loop thread, and the first build embeds every tracked concept with SentenceTransformer — a multi-minute stall of all capture. Pre-warm the knowledge graph inside `warm_up_all_pipelines` (already a background thread at tracker startup) so `get_graph()` is a cached call on the hot path.
- [x] **Micro-quiz actually reaches the browser.** `loop.py` broadcasts `micro_quiz` over Socket.IO (`realtime.py`), and `app.py` does run `socketio.run` — but the frontend has **no socket client at all**, so the interrupt broadcasts into the void and the Quiz page is only manual/polled. Fix: add `socket.io-client`, connect from `MainLayout`, subscribe to `micro_quiz`, and render a modal interrupt (concept, question, 4 options, difficulty) whose answer POSTs to `/quiz/answer` (feeds SM-2). This turns the micro-quiz from dead broadcast into the delivered interrupt Phase 9's capture deserves.
- [x] **Tests + docs.** Unit tests for the `/intent/recent` cooldown (first call returns and stamps `prompted_at`, immediate second call returns null, answered rows never re-prompt), `should_show_quiz` threshold + session gating, and graph pre-warm. Update README/AGENTS test counts and mark this phase done in the plan.

---

## Definition of done

A grader, recruiter, or future-you should be able to:
1. Clone the repo fresh.
2. Run `pip install -r requirements.txt` and `npm install` with zero manual fixes.
3. Run migrations, start `main.py` and `web/app.py`, start the frontend dev server.
4. See live data flow from screen/audio capture → knowledge graph → dashboard, including the Graph and Quiz pages.
5. Run `pytest tracker_app/tests/` and see it pass, with no fake "tests" in the mix.
6. Read the README/ADRs and find them consistent with what the code actually does.
7. Trust that a tracked concept in the knowledge graph reflects something they were actually studying, not just something that happened to be on screen.
8. Use the app through a real study session and find that neither the feedback toast nor the quiz interrupt fires more often, or at a worse moment, than a human would actually tolerate — verified by using it, not just by reading the trigger code.

**Status: Phase 10 implemented (115 tests, CI pending). Remaining: live study-session E2E of the toast cooldown + quiz push, then finalize.**
