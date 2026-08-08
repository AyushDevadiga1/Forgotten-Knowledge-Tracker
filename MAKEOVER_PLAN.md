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

### 10.1 — [RESOLVED] The intent-feedback toast was firing roughly every 10 seconds during any study session

**The problem, as found:** `TRACK_INTERVAL = 5` means the loop iterates every 5 s, and `monitor.process_intent()` ran unconditionally every cycle, inserting a fresh unlabeled `IntentPrediction` row each time. `IntentFeedbackToast.tsx` polled every 10 s for *any* unanswered row, with no cooldown or dismissal memory — so the moment one prediction was answered, a newer one (created in the last 5–10 s) was already waiting. During a study session, that meant a "was this correct?" popup roughly every 10 seconds, indefinitely.

**Fix applied:** `IntentPrediction` gained a `prompted_at` column. `GET /intent/recent` now only ever surfaces a row that is (a) unanswered, (b) never previously shown, and (c) at least `TOAST_COOLDOWN_MINUTES` since the last prompt — and it stamps `prompted_at` immediately so the same row is never re-shown. The toast also got a dismiss (✕) button. Verified by reading `web/api.py`'s `get_recent_intent()` and the current `IntentFeedbackToast.tsx` directly — the cooldown and stamping logic is real and matches this description.

### 10.2 — [RESOLVED] The micro-quiz "interrupt" wasn't reaching the user, and the trigger could stall the whole tracker

**The problem, as found:** `quiz_engine.py`'s `should_show_quiz()` was well-tuned on paper (cooldown, idle-cycle threshold, attention gate), but `package.json` had no `socket.io-client` dependency and nothing in `src/` listened for the `micro_quiz` Socket.IO broadcast — it fired into the void. The only path that actually reached a user, `GET /quiz/current`, bypassed `should_show_quiz()` entirely. A second, more serious issue surfaced during this investigation: the trigger's first call to `get_graph()` builds the knowledge graph synchronously, embedding every tracked concept with SentenceTransformer *inside the tracking loop thread* — a multi-minute stall of all capture (OCR/audio/webcam) the first time a quiz condition was met.

**Fix applied:** `socket.io-client` added; `MicroQuizModal.tsx` connects a socket, listens for `micro_quiz`, and renders a real modal interrupt (options, correct/incorrect feedback, posts to `/quiz/answer`) — verified present and mounted in `MainLayout.tsx`. `should_show_quiz()` gained a `session_active` parameter so it can never fire outside a study session. `warm_up_all_pipelines()` (already a background thread at startup) now pre-builds the knowledge graph, so `get_graph()` is a cached call by the time the loop's hot path needs it — verified in `loop.py`.

### 10.3 — [RESOLVED] Quiz timing redesigned: interrupt on a pause while the user is present

`IDLE_CYCLES_REQUIRED` was raised from 3 to 12 (~60 s instead of ~15 s) as part of the 10.2 fix — a good change, but it addresses *speed*, not *timing logic*. `should_show_quiz()` still required `attention_score < 35` ("user is away / zoned out") when webcam is enabled — i.e. it was tuned to catch the moment someone has stepped away or mentally checked out, precisely when they won't see or answer a modal interrupt.

**Fix applied:** flipped the attention gate to the opposite convention. The trigger now fires on a short pause (idle ≥ 12 cycles) *while attention is still at least `ATTENTION_PRESENT_MIN` (35)* — the user is present and between tasks, so the interrupt actually reaches someone able to answer it. When attention drops below 35 the quiz is suppressed (stepped away / zoned out → modal would be missed). Webcam-disabled path is unchanged (idle cycles are sufficient signal). Verified by `test_quiz_trigger.py` (10 tests incl. the new floor guard).

- [x] Revisit the trigger condition itself, not just its speed: consider firing on a short pause with attention still reasonably high, rather than on sustained idle + low attention. This is a design decision about what "a good moment to interrupt" means, not a number to tune.

### 10.4 — [RESOLVED] The feedback toast now shows enough context to answer accurately

`IntentFeedbackToast.tsx` showed only the predicted label and a confidence percentage — no timestamp, no window/context. Predictions are generated every 5 seconds, so a user asked "was this STUDYING?" with no indication of *when* may not remember what they were doing at that exact moment. Since ADR-003's whole premise is retraining the classifier on *real* corrective feedback, answers the user can't actually judge accurately quietly reintroduce noisy labels into the exact pipeline that was fixed to avoid that. Separately, the toast's "DATA COLLECTION" header was clinical/surveillance-flavored.

**Fix applied:** the toast now shows a relative timestamp ("just now", "2 min ago") derived from the prediction's UTC timestamp and the active window title (truncated, with full title on hover), right above the "Was this correct?" prompt. The header was softened from "DATA COLLECTION" to "Quick Check". `GET /intent/recent` now returns `window_title` alongside the existing `timestamp`.

- [x] Show a timestamp and/or window title alongside the predicted label so the user has enough information to answer accurately.
- [x] Reconsider the "DATA COLLECTION" framing — costs nothing to soften, changes how the prompt lands.

---

### 10.5 — Verification & wrap-up

- [ ] **Live study-session run** confirming the toast cooldown actually feels right in practice (not just correct in code) — 5-minute default may still be too frequent for some, worth using the app to judge, not just reading the number. *Code-level verification done; the remaining judgment is a manual "use it for a real session" check.*
- [x] Test-suite coverage confirmed: `/intent/recent` cooldown (first call returns + stamps `prompted_at`, immediate second call returns null, answered rows never re-prompt — `test_intent_toast_cooldown.py`), `should_show_quiz`'s `session_active` gating + attention/cooldown logic (`test_quiz_trigger.py`), and the graph pre-warm (`test_warmup.py`, added — `warm_up_all_pipelines` calls `get_graph()`). Suite is now **145 tests**; README/AGENTS claims updated to match.

---

## Phase 11 — Core logic correctness (crucial — found via full code audit)

This phase exists because a systematic read of every scheduling/graph/classifier module (not just the frontend-facing pieces) found several places where the code *looks* correct — reasonable variable names, plausible-looking formulas, docstrings that describe the right behavior — but a real bug means it doesn't actually do what it claims. These are prioritized by how much of the app's core value they silently undermine. Everything below is confirmed by reading the current code and tracing the actual call paths, not inferred from structure.

### 11.1 — [CRITICAL] ADR-003's "train on real user feedback" pipeline is completely non-functional

ADR-003 (Phase 5) justifies keeping the RandomForest intent classifier by claiming it now retrains on real user corrections instead of only synthetic data. Tracing the actual data path shows this never happens:

- `activity_monitor.py`'s `IntentValidator.log_prediction()` stores the **window title** in `IntentPrediction.context_keywords` (it's literally passed `context=window_title` from `loop.py`) — not the 6-value feature vector `[ocr_keyword_count, audio_val, attention_score, interaction_rate, keyword_avg_score, audio_confidence]` that was actually fed into the classifier for that prediction.
- `web/api.py`'s `FeedbackService.record_feedback()` copies that same window-title string directly into `FeedbackTrainingSample.feature_vector` — a column whose own docstring says `# JSON: [f1, f2, f3, f4, f5, f6]`.
- `scripts/train_models_from_logs.py`'s `load_feedback_samples()` does `feats = json.loads(s.feature_vector)` inside a bare `try/except: pass`. A window title (e.g. `"Chrome - YouTube - some video"`) is not valid JSON, so this raises and is silently swallowed for essentially every single feedback row. `X_fb`/`y_fb` end up empty (or near-empty), so the `--include-feedback` augmentation in `main()` adds nothing, and the auto-retrain triggered every 50 corrections (`FeedbackService.maybe_trigger_retrain`) just re-trains on the same 100% synthetic dataset it always has.

**Net effect:** every "NO, this was wrong" correction a user submits is captured, stored, and then silently discarded at training time. ADR-003's core claim — that this is no longer the synthetic-data problem ADR-002 identified — is not actually true of the running system.

- [x] Store the actual 6-feature vector used at prediction time (not the window title) — e.g. have `predict_intent()` return the feature array alongside the prediction, or recompute it identically at feedback time, and JSON-encode *that* into `IntentPrediction.context_keywords` / `FeedbackTrainingSample.feature_vector`.
- [x] Add a test that round-trips this: submit feedback, confirm `FeedbackTrainingSample.feature_vector` parses as a 6-element JSON list, confirm `load_feedback_samples()` actually picks it up.
- [x] Consider keeping the window title too, but in a separate column — it's useful context, just not a substitute for the feature vector.

### 11.2 — [CRITICAL] The knowledge graph's `memory_score` is frozen at 0.3 for every concept, forever

`tracking/knowledge_graph.py`'s `add_concepts()` sets `memory_score=0.3` when a node is first created. Nothing in the codebase ever updates it afterward — confirmed by reading every function in `knowledge_graph.py` and `activity_monitor.py`'s `process_concepts()` (the only place concept-processing happens). The *real* spaced-repetition state — `interval`, `memory_strength`, `lambda_personalised`, `next_review` — is correctly computed and updated in the separate `TrackedConcept` SQL table by `concept_scheduler.py`. The in-memory NetworkX graph and the SQL table have simply diverged: one is live, the other is a frozen snapshot from node-creation time.

**Net effect, both confirmed by tracing the callers:**
- `get_graph_stats()`'s `avg_memory_score` (shown on the Graph page) will always read ≈0.3 no matter how much real progress has been made, because every node is stuck at its initial value.
- `generate_micro_quiz()`'s "prefer concepts with `memory_score < 0.65`" filter is trivially true for *every* node (0.3 < 0.65, always), so it provides zero actual prioritization. The quiz doesn't test your weakest concept — it tests whatever `pool.sort()`'s stable-sort tiebreaking happens to put first, which in practice is close to insertion order. The headline "tests you on what you're most likely to forget" feature isn't doing that.

- [x] Sync `TrackedConcept.relevance_score` / an AWFC-computed retention value into the graph node's `memory_score` whenever a concept is reviewed or re-encountered — e.g. inside `ConceptScheduler.add_concept()`/`schedule_next_review()`, or as part of `sync_db_to_graph()`.
- [x] Add a test asserting `memory_score` actually changes after a review, not just that it exists.

---

### 11.3 — [HIGH] The concept-drift endpoint is called with no data, so it can never report anything but "stagnant"

`web/api.py`'s `/graph/drift/<concept>` route calls `compute_concept_drift(concept, [])` — always an empty list for `current_session_keywords`, the exact input the whole algorithm is built around comparing against historical neighbours. With `current_neighbours` always empty, `compute_concept_drift()`'s own logic (`if not current_neighbours: status = 'stagnant'`) means this endpoint can only ever return `drift_score: 0.0, status: 'stagnant'` (or `'new'`) for literally any concept passed to it. The drift-detection algorithm itself may be reasonable; it's simply never given real data to work with at its one production call site.

- [x] Pass real data: the concepts encountered in the current/recent study session (e.g. `monitor.session_concepts`, already tracked by `ActivityMonitor`), not a hardcoded empty list.

### 11.4 — [MEDIUM] `compute_concept_drift`'s status classifier has a dead branch

Even setting 11.3 aside, the classification logic itself can't produce the 4 statuses its own docstring promises (`'new'|'evolving'|'stable'|'stagnant'`):

```python
if not current_neighbours:
    status = 'stagnant'
elif drift > 0.6:
    status = 'evolving'
elif drift > 0.2:
    status = 'stable'
else:
    status = 'stable'          # ← same result as the branch above
```

The `drift > 0.2` branch and the final `else` both resolve to `'stable'` — reads like an intended fourth category (e.g. distinguishing "drifting a little" from "barely changed") that never got written.

- [x] Decide what the fourth bucket should actually be and give it a distinct condition, or collapse the two branches intentionally and update the docstring to match 3 real statuses instead of 4.

### 11.5 — [MEDIUM] Knowledge-gap detection mixes two incompatible similarity spaces

The graph's edges (what counts as "already connected," used to exclude gap candidates) are built in `add_concepts()` using SentenceTransformer `all-MiniLM-L6-v2` cosine similarity, threshold `0.7`. `find_knowledge_gaps()` computes its *own* similarity independently, using `spacy.load("en_core_web_sm").similarity()`, threshold `0.55`. These are different models producing different, uncalibrated similarity scales — `en_core_web_sm` in particular is spaCy's small English model, which doesn't ship real pretrained word vectors; spaCy's own documentation notes similarity results from this model are unreliable. A 0.55 spaCy-similarity threshold has no principled relationship to the 0.7 MiniLM-cosine threshold used to build the graph it's operating on.

- [x] Use the same embedding source for gap-detection as for edge-building (the MiniLM embeddings are already computed and could be reused/cached from `add_concepts()`), or explicitly document why a second, different similarity metric is intentional and recalibrate its threshold against real data rather than a guessed number.

### 11.6 — [HIGH] Two parallel, inconsistent SM-2 implementations exist in the same codebase

`sm2_memory_model.py`'s `SM2Scheduler.calculate_next_interval()` is a correct, standard SM-2 implementation with real test coverage (`test_sm2.py`) — but it's only used by the separate, manually-added flashcard system (`LearningItem`, via `learning_tracker.py`). The auto-tracked concept system (the actual core feature) uses `concept_scheduler.py`'s `ConceptScheduler.schedule_next_review()`, which reimplements SM-2 by hand instead of calling the tested one, and diverges from it in two concrete ways:

- **No repetition counter.** The only signal for "how far along is this concept" is `interval <= 1`. A brand-new concept's `interval` defaults to `1`, so its *first* successful review jumps straight to a 3-day interval (`new_interval = 3 if interval <= 1 else round(interval * ease)`) — skipping the canonical SM-2 1-day initial-reinforcement step entirely, for every concept, every time. The same collapse happens on recovery from any failure, since a failure also resets `interval` to `1`.
- **Inconsistent failure penalty.** On failure it applies a flat `ease - 0.2`, while success uses the graduated SM-2 formula (`0.1 - (5-q)*(0.08+(5-q)*0.02)`) computed a few lines below but never applied to the failure case. The two penalty schemes aren't reconciled with each other.

- [x] Either have `concept_scheduler.py` call the tested `SM2Scheduler` directly (adapting it to work off `TrackedConcept` rows), or add an actual repetition counter to `TrackedConcept` and fix the interval/ease logic to match the standard algorithm consistently for both success and failure.
- [x] `sm2_memory_model.py`'s own `SM2Scheduler` also uses `interval=3` for the second successful review where canonical SM-2 uses `6` — worth a deliberate decision (keep 3, or match the original) rather than an unexplained deviation from an algorithm the docstring calls "research-validated defaults from SuperMemo."

### 11.7 — [MEDIUM] Naive datetime mix-up between UTC and local time across two subsystems

Every `TrackedConcept`/`ConceptEncounter`/`IntentPrediction`/`FeedbackTrainingSample` timestamp (both the SQLAlchemy column defaults in `db/models.py` and every write in `concept_scheduler.py`) uses `datetime.utcnow()`. Every `LearningItem`/`ReviewHistory` timestamp (`learning_tracker.py`, `db/repository.py`'s `LearningRepository`) uses `datetime.now()` (local). Each subsystem is internally self-consistent, but two confirmed places compare across the boundary:

- `LearningRepository.get_learning_today()` computes `today_start`/`today_end` from local `datetime.now()`, then filters `TrackedConcept.last_seen >= today_start` — a UTC-stored column compared against a local-time boundary. "Concepts studied today" will be wrong by the size of the local UTC offset around midnight.
- `LearningTracker._compute_streak()` computes "today" as `datetime.utcnow().date()`, then checks it against `ReviewHistory.timestamp` values, which were written using local `datetime.now()`. For a user ahead of UTC (e.g. IST, UTC+5:30), a review done in the local early-morning hours can log to "today" locally while UTC still considers it "yesterday," silently breaking the streak count.

- [x] Pick one convention (UTC is the safer default) and use it everywhere timestamps are written or compared — this is the kind of bug that stays invisible in same-timezone testing and only shows up for real users in non-UTC zones.

### 11.8 — [FIXED] Passive re-encounters were silently discarding recalibrated lambda

Found while independently re-verifying the 11.2 fix (not part of the original audit). `ConceptScheduler.add_concept()`'s existing-concept branch unconditionally recomputed `lambda_personalised` from `compute_awfc_lambda(DEFAULT_LAMBDA, attention_at_encoding)` on *every* passive re-encounter. `schedule_next_review()` separately calls `recalibrate_lambda()` after 5+ real reviews to personalise the decay rate based on actual observed recall — but that personalisation got wiped the next time the same concept was simply re-seen on screen via OCR, which happens far more often than it gets quizzed. The recalibration survived only until the next passive encounter.

**Fix applied directly:** `add_concept()` now only does the full attention-based recompute for a concept with zero repetitions (nothing to protect yet). Once `repetitions > 0` — meaning `schedule_next_review()` has personalised it at least once — a passive re-encounter nudges lambda 90/10 toward the attention-based estimate instead of replacing it outright, so the review-based personalisation persists rather than resetting on the next OCR pass.

---

## Definition of done
1. Clone the repo fresh.
2. Run `pip install -r requirements.txt` and `npm install` with zero manual fixes.
3. Run migrations, start `main.py` and `web/app.py`, start the frontend dev server.
4. See live data flow from screen/audio capture → knowledge graph → dashboard, including the Graph and Quiz pages.
5. Run `pytest tracker_app/tests/` and see it pass, with no fake "tests" in the mix.
6. Read the README/ADRs and find them consistent with what the code actually does.
7. Trust that a tracked concept in the knowledge graph reflects something they were actually studying, not just something that happened to be on screen.
8. Use the app through a real study session and find that neither the feedback toast nor the quiz interrupt fires more often, or at a worse moment, than a human would actually tolerate — verified by using it, not just by reading the trigger code.
9. Trust that the numbers on screen are real: a concept's memory score actually reflects its review history, a "wrong" click on the feedback toast actually improves the next model retrain, and the drift/gap features report something other than a hardcoded default.

**Status: Phase 10 fully resolved (10.1–10.5; only the manual live-session feel-check under 10.5 remains — everything code-verifiable is done and tested; 10.3 quiz timing flipped to interrupt on a pause while the user is present, 10.4 toast shows timestamp + window title and drops the "DATA COLLECTION" framing). Phase 11 independently re-verified end-to-end — all 7 audit bugs (11.1–11.7) traced through their actual call paths and confirmed genuinely fixed, including their test coverage: 11.1 feedback pipeline stores the real 6-feature vector and `train_models_from_logs.py` picks it up (legacy bad rows skip gracefully); 11.2 graph `memory_score` syncs live AWFC state on every add_concept/schedule_next_review, not just at load time; 11.3 drift endpoint uses real session concepts; 11.4 dead `stable` branch gone; 11.5 gap detection reuses the same embeddings as edge-building; 11.6 shared SM-2 constants + real `repetitions` counter, deliberate 3-day second interval documented; 11.7 UTC everywhere, cross-subsystem comparisons confirmed correct. One additional bug (11.8) found during this re-verification and fixed directly: passive OCR re-encounters were overwriting `recalibrate_lambda()`'s personalisation on every sighting — now only replaces it before any reviews exist, nudges gently afterward (regression-tested in `test_concept_scheduler.py`). Suite is now 145 tests.**
