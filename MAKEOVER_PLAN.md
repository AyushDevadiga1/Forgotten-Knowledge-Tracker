# FKT Makeover Plan — Evidence-Based Architectural Audit

> **Ground rules for this document:**
> - *Working behavior* is documented as-is.
> - *Broken behavior* is distinguished from *unclear/accidental behavior*.
> - No recommendations are made unless a real problem was observed.
> - Every finding cites the file and line range where it was confirmed.
> - This plan is a living document — earlier assumptions will be corrected as investigation deepens.

---

## 1. System Map — What the System Actually Does

FKT is a two-process application:

| Process | Entry point | Purpose |
|---|---|---|
| Tracking loop | `tracker_app/main.py` → `tracking/loop.py` | Background data collection |
| Dashboard | `tracker_app/web/app.py` | Flask + React UI |

### Data flow (confirmed, not assumed)

```
Screen  ──► OCR pipeline      ──► keywords dict
Mic     ──► audio pipeline    ──► {audio_label, confidence}
Webcam  ──► webcam_pipeline   ──► {attentiveness_score, …}
KB/Mouse ─► CLE module        ──► cle_score

All 4 feeds ──► predict_intent() ──► intent_label

If session_active AND intent_label in SESSION_ALLOWED_INTENTS:
    ──► ActivityMonitor.process_concepts()
        ──► ConceptScheduler.add_concept()
            ──► TrackedConcept (SQLite)
            ──► ConceptEncounter (SQLite)
            ──► sync_concept_to_graph()
                ──► knowledge_graph (networkx, in-memory + .pkl cache)

session_state.json ──► shared toggle (write: Flask API; read: tracking loop)
```

### SM-2 / AWFC model (confirmed)

Two distinct SM-2-capable subsystems exist:

1. **`LearningItem`** (manual flashcards) — reviewed via `ReviewPage`, uses
   `learning/learning_tracker.py` which drives `sm2_memory_model.py`.
2. **`TrackedConcept`** (auto-captured) — reviewed via `QuizPage` /
   `MicroQuizModal`, uses `concept_scheduler.py:schedule_next_review()`.

Both systems implement the same canonical SM-2 formula but in separate classes,
with no shared base class.

---

## 2. Issues by Severity

### 2.1 CRITICAL

---

#### [C-1] Privacy filter is cosmetic, not structural

**Status: RESOLVED** — `ocr_module.py` now hard-imports `sanitize_text_for_storage`
and `is_sensitive_window` at module level; the `try/except ImportError` silent pass
is gone and `should_skip_window()` delegates to `privacy_filter.is_sensitive_window()`.
Regression coverage: `tests/test_ocr_privacy_gate.py`.

**File:** `tracking/privacy_filter.py`, `tracking/ocr_module.py:206-220`

**Behavior observed:** `sanitize_text_for_storage()` catches credit cards, SSNs,
emails, IPs, and API keys using regex — good. But the threshold to **skip** an
entire capture is `> 3` sensitive items (`should_skip_capture` line 101). This
means a page with 1-3 credit card numbers is **sanitized but still stored**, not
rejected entirely.

More critically, `privacy_filter.py` is imported inside a `try/except ImportError`
block in `ocr_module.py` (line 207). If the import fails for any reason, the
**entire privacy layer is silently skipped** with no log. A user would have no
indication their data is being stored unredacted.

**Actual impact:** An OCR capture containing a password typed in plain text on
screen (e.g., a notes app) will be stored unless the word `password` also appears
in the **window title**. The content-level filter only acts after capture.

**What should happen:** Privacy checks should be a mandatory structural gate, not
a best-effort import. The `ImportError` silent pass is the most dangerous pattern
in the codebase.

---

#### [C-2] `session_state.json` — `started_at` never resets on restart

**Status: RESOLVED** — `start()` now always stamps `started_at = now` and clears
`stopped_at`, so restarts and crash-recovery both reset the clock.
Regression coverage: `test_session_state.py::test_restart_resets_started_at` and
`test_start_after_crash_resets_stale_clock`.

**File:** `tracking/session_state.py:48-58`

```python
def start() -> dict:
    with _lock:
        state = _load()
        now = datetime.utcnow().isoformat()
        state["active"] = True
        if not state.get("started_at"):   # ← only sets if currently None
            state["started_at"] = now
        state["stopped_at"] = None
        _save(state)
        return state
```

**Behavior observed:** `started_at` is only written on the **first** start. If a
session is stopped (which sets `stopped_at` but does NOT clear `started_at`) and
then restarted, the new session's elapsed timer will count from the *previous*
session's start time. After a crash that leaves `stopped_at = None`,
`elapsed_seconds` in `get_status()` will report wall-clock time since the
crashed session began — potentially hours or days.

The threading `_lock` only protects within-process writes; the two processes share
no OS-level lock. On Windows `Path.replace()` is atomic, so reads are safe in
practice, but the semantics aren't documented.

---

#### [C-3] Authentication exists but is never activated

**File:** `web/auth.py:15`, `web/app.py` (entire file)

```python
_NO_AUTH = os.getenv("NO_AUTH", "true").lower() == "true"  # Default: no auth in dev
```

`apply_auth_to_blueprint()` is never called in `app.py`. The entire auth module
is inert. For a personal localhost tool this is a deliberate tradeoff, but:

- The JSON mutation endpoints (`POST /items`, `POST /reviews`, `POST /session/start`)
  have no CSRF protection on the JSON paths (Flask-WTF CSRF only fires on form
  submissions, not JSON `Content-Type` bodies).
- Any web page the user has open can silently trigger these endpoints via fetch.

---

#### [C-4] Audio training data is entirely synthetic

**Status: RESOLVED** — the synthetic GaussianNB trainer (`train_audio_classifier`),
its model loading, and its training `__main__` block were removed from
`audio_module.py`; `classify_audio()` always uses the energy-based heuristic. The
removed trainer is documented in `models/README.md`. Regression coverage:
`tests/test_audio_heuristics.py`.

**File:** `tracking/audio_module.py:180-234`

`train_audio_classifier()` generates 600 samples per class from `numpy.random`.
The "speech" distribution is hardcoded MFCC shapes with no real audio. The trained
model will generalize poorly to real-world microphone input. The energy-based
fallback (`energy_based_classification`) is actually more honest. The training
function is a stub that creates a false sense of "trained" classifier quality.

---

### 2.2 HIGH

---

#### [H-1] Two parallel SM-2 implementations with diverging semantics

**Status: RESOLVED (verified)** — Phase 11.6 gave `TrackedConcept` a real
`repetitions` counter and unified all constants/formulas between the two
subsystems. The remaining divergence was closed and locked in with
`test_concept_scheduler.py::test_matches_tested_sm2_scheduler_across_quality_sequence`,
which drives the same mixed success/failure quality sequence through both
`SM2Scheduler` and `concept_scheduler.schedule_next_review()` and asserts
identical interval, ease, and repetitions at every step. Correction to the audit
below: `LeitnerSystem` is **not** dead code — it is imported by
`learning/learning_tracker.py:8` and invoked at `:118` for the
`algorithm="leitner"` path (see [L-1]).

**Files:** `learning/sm2_memory_model.py:67-152`, `learning/concept_scheduler.py:116-193`

Both implement SM-2. `concept_scheduler.py` imports constants from
`sm2_memory_model.py` but re-implements the loop body. The ease factor field
is stored as `TrackedConcept.memory_strength` in the database but is read with
`getattr(tracked, "memory_strength", 2.5)` — a silent default of 2.5 means a
concept with a NULL ease factor in the DB will always start with DEFAULT ease,
silently discarding any previous calibration.

The `LeitnerSystem` class (lines 196–245 of `sm2_memory_model.py`) is dead code —
fully implemented, never imported, never called.

---

#### [H-2] Sparklines on Overview page display random fabricated data

**Status: RESOLVED** — new `GET /api/v1/stats/trend?days=N` backed by
`LearningRepository.get_review_trend()` (real per-day reviews/correct/added/
mastered/due from stored timestamps). `OverviewPage.tsx` fetches the trend and
`miniSparkline(trend, pick)` renders it; the fabricated random `miniSparkline()`
is gone. Regression coverage: `test_api.py::TestAPIStatsTrend`.

**File:** `web/frontend/src/pages/OverviewPage.tsx:18-22`

```tsx
function miniSparkline(base: number): { v: number }[] {
  return Array.from({ length: 7 }, (_, i) => ({
    v: Math.max(0, base + Math.round((Math.random() - 0.5) * base * 0.2) + i),
  }))
}
```

Every component render (triggered every 5 seconds by the session poll) calls
`miniSparkline()` and gets a **different** random array. The sparklines flicker
and display fabricated trends. This is misleading UX — a user who watches their
"mastery trend" go up and down is watching noise. There is no real time-series
endpoint to back this up.

---

#### [H-3] `FeedbackService` intent cooldown has a TOCTOU race

**Status: RESOLVED** — `/intent/recent` now claims the prompt with an atomic
`UPDATE ... WHERE prompted_at IS NULL AND user_feedback IS NULL` (SQLAlchemy
`update()` + rowcount check); the losing concurrent request gets a null result
instead of double-firing the toast. Regression coverage:
`test_intent_toast_cooldown.py::TestAtomicClaim`.

**File:** `web/api.py:33-104`

`GET /intent/recent` reads `prompted_at`, decides if the prediction is eligible,
and then writes `prompted_at` — all in the same HTTP handler but without a
database row lock. Two simultaneous requests (two open browser tabs) can both
read the eligible state before either writes, causing the toast to fire twice.

---

#### [H-4] `_idle_cycles` and `_last_quiz_time` are module-level globals not reset between runs

**Files:** `tracking/loop.py:218`, `tracking/quiz_engine.py:23`

If `track_loop()` is called more than once in the same process (test restarts,
signal-based reloads), these counters carry state from the previous run. The
quiz trigger could fire prematurely in the second run, or be suppressed for the
full cooldown period from the previous session.

---

#### [H-5] Knowledge graph grows without bound; no eviction

**File:** `tracking/knowledge_graph.py`

No node limit, no TTL, no low-relevance pruning. After months of use the `.pkl`
file can be large enough that `get_graph()` noticeably blocks the tracking loop.
Each node also stores a 384-dimensional float32 embedding (1.5 KB per node);
10,000 nodes = ~15 MB resident just for embeddings.

---

### 2.3 MEDIUM

---

#### [M-1] `ActivityMonitor.session_concepts` is an unbounded list

**File:** `tracking/activity_monitor.py:145, 217`

Every processed concept is appended to a list. For `end_session()` only a
`Counter` and a `len(set(...))` are needed. Over a long session this list can
hold thousands of duplicated strings. A `Counter` accumulator would avoid the
issue entirely.

---

#### [M-2] `extract_keywords()` discards compound keyword forms

**File:** `tracking/ocr_module.py:268-286`

The camelCase splitter (step 3) destroys the original compound token and replaces
it with its parts. `backPropagation` → `back`, `propagation`. If TF-IDF scored
the compound highly, that score is now split across two lower-value tokens. The
compound form — which is often the better concept label — is lost.

---

#### [M-3] `QuizPage.tsx` and `MicroQuizModal.tsx` duplicate identical UI logic

**Status: RESOLVED** — the duplicated `handleSelect()`/`optionClass()`/result
banner were extracted into a shared `hooks/useQuizAnswer.ts` (guard + selected/
answerState + fire-and-forget SM-2 submission + option styling) and a shared
`components/QuizResultBanner.tsx` (banner JSX; the Next/Close action button is
passed as a `ReactNode`). Both pages now call the hook; `QuizPage` adds its
score tally from the hook's returned correctness value. Verified: `npx tsc --noEmit`.

**Files:** `web/frontend/src/pages/QuizPage.tsx:66-90`,
`web/frontend/src/components/MicroQuizModal.tsx:28-51`

`handleSelect()`, `optionClass()`, and the result banner are character-for-character
identical in both components. Any fix or style change must be applied in both.

---

#### [M-4] Date filter in `TrackingRepository` uses `LIKE` instead of range

**Status: RESOLVED** — `get_daily_summary` now filters
`start_time >= day_start` and `< next_day` (real datetime range). Regression
coverage: `test_api.py::TestDailySummaryRange`.

**File:** `db/repository.py:183`

```python
.filter(TrackingSession.start_time.like(f"{date_str}%"))
```

String `LIKE` for date filtering is fragile (breaks if format changes) and
prevents SQLite from using an index. A `>= today_start` and `< tomorrow_start`
range filter is correct.

---

#### [M-5] Two independent definitions of `SENSITIVE_WINDOW_KEYWORDS`

**Status: RESOLVED** — resolved as part of [C-1]: the local list and local
`should_skip_window()` were removed from `ocr_module.py`; `privacy_filter.py`
holds the single canonical keyword list and `ocr_module` delegates to it.
Regression coverage: `test_ocr_privacy_gate.py` asserts union coverage of both
old lists (`authentication`, `payment`, `health`, `prescription`, ...).

**Files:** `tracking/ocr_module.py:60-63`, `tracking/privacy_filter.py:28-33`

The lists differ: `privacy_filter.py` includes `authentication`, `payment`,
`medical`, `health`, `prescription` which the OCR module omits.
`should_skip_window()` in `ocr_module.py` is a local reimplementation of
`is_sensitive_window()` in `privacy_filter.py`. One should call the other.

---

#### [M-6] Lambda recalibration uses a single review's quality as cumulative success rate

**Status: RESOLVED** — migration 010 adds `review_count`/`correct_count` to
`tracked_concepts`; `schedule_next_review()` increments them on every quiz review
and recalibration now passes the true cumulative
`correct_count / review_count` with `n_reviews = review_count` (gate raised from
the old `frequency_count` OCR-encounter proxy to `review_count >= 5`). Regression
coverage: `test_concept_scheduler.py` — counters test, "no recalibration before 5
reviews" test, and a deterministic test proving the cumulative rate (4/5) is used
instead of the last rating (quality 2 → 0.4).

**File:** `learning/concept_scheduler.py:172-174`

```python
correct_rate = (quality / 5.0)  # approximate from single rating
```

`recalibrate_lambda()` expects a cumulative success rate over `n_reviews`.
Passing the last review's quality (0–1 scaled) conflates one data point with
a historical average. The comment acknowledges it's approximate but doesn't
fix the semantic error.

---

#### [M-7] `BubbleGraph` in `GraphPage.tsx` renders a spoke diagram, not a graph

**Status: RESOLVED** — `get_graph_stats()` now returns a real `edges` list
(`[source, target, weight]` among the visible top concepts). `BubbleGraph`
receives it and draws only actual semantic links, with stroke width/opacity
scaled by weight; the fabricated "HUB" node and spokes are gone (the backend
graph has no such node). An honest "no semantic links" caption shows when the
visible set has no edges. Backend regression coverage:
`test_knowledge_graph.py::test_graph_stats_includes_real_edges` (verifies
exclusion of edges to out-of-set nodes and weight ordering). Frontend:
`npx tsc --noEmit`.

**File:** `web/frontend/src/pages/GraphPage.tsx:37-72`

The visualization draws all concepts as equidistant spokes from a central "HUB"
node. It does not use edge data (the API returns `top_concepts: string[]` with no
edges). The total_edges counter is displayed but the edges are never drawn. The
graph misleadingly implies all concepts are equally and directly related to a
central hub, which contradicts the actual weighted semantic graph in the backend.

---

### 2.4 LOW / DEAD CODE / STYLE

---

#### [L-1] Dead code: `LeitnerSystem` class

**Status: NOT A BUG (audit corrected)** — the audit's claim that `LeitnerSystem`
is "never imported or called" is wrong. It is imported by
`learning/learning_tracker.py:8` and invoked at `:118` for the
`algorithm="leitner"` path (and imported by `tests/test_new_system.py`). It is
live code for an alternate review algorithm; no action taken.

**File:** `learning/sm2_memory_model.py:196-245`

Fully implemented, never imported or called.

---

#### [L-2] Dead code: entire `web/auth.py` module

**File:** `web/auth.py:1-60`

Both `@require_api_key` decorator and `apply_auth_to_blueprint()` are defined.
Neither is called anywhere in `app.py`. The module is entirely inert.

---

#### [L-3] Misleading log message in `db_module.py`

**File:** `db/db_module.py:18`

```python
logger.info("SQLAlchemy tables constructed: sessions, multi_modal_logs, memory_decay, etc.")
```

`multi_modal_logs` and `memory_decay` do not exist as table names in `models.py`.
These are artifacts from a previous schema.

---

#### [L-4] `IntentFeedbackToast` dismissed state resets on unmount

**Status: RESOLVED** — dismissal is now persisted per prediction in
`localStorage` (`fkt:dismissed-intent:<id>`), so a dismissed prediction stays
hidden across navigation and page reloads. The backend already stamps
`prompted_at` on first serve (atomic claim), so the same prediction can never be
surfaced twice anyway — the local store is belt-and-suspenders for the toast's
own display window. Verified: `npx tsc --noEmit`.

**File:** `web/frontend/src/components/IntentFeedbackToast.tsx:26`

`const [dismissed, setDismissed] = useState(false)` — dismiss state is component-local.
Navigating away and back causes the same prediction to reappear. No backend
persistence for "user has seen and dismissed this prediction".

---

#### [L-5] `export_tracking_data()` can fail with an empty dirname

**File:** `tracking/activity_monitor.py:274`

```python
os.makedirs(os.path.dirname(output_file), exist_ok=True)
```

If `output_file` has no directory component, `os.path.dirname()` returns `''`
and `os.makedirs('')` raises `FileNotFoundError`. Harmless with the default
`DATA_DIR`-based path, but breaks on any manually provided bare filename.

---

#### [L-6] Frontend sends unnecessary `{}` body on session toggle

**File:** `web/frontend/src/api.ts:131, 138`

`POST /session/start` and `POST /session/stop` ignore the request body. Sending
`JSON.stringify({})` implies future parameterization that doesn't exist.

---

## 3. Architecture Observations

### What works well and should be preserved

| Pattern | Why it works |
|---|---|
| Lazy pipeline loaders (`loop.py` `get_ocr_pipeline()` etc.) | No heavy imports at startup; cold-start stays fast |
| `ThreadPoolExecutor` with 8-second timeout | Slow pipeline can't block the tracking cycle |
| CPU-adaptive sampling intervals | Reduces tracker footprint during user-intensive work |
| `session_state.json` atomic write (tmp→replace) | Safe single-writer IPC; correct for this use case |
| `is_plausible_concept()` quality filter | Real, tested OCR noise gate |
| Session-gated + intent-gated concept capture | Prevents noise from non-study activity |
| Background warm-up thread | Moves model cold-start latency away from first cycle |

### Structural risks (not bugs, but design constraints)

1. **JSON file IPC does not scale.** The Start/Stop toggle works via file IPC.
   Any new cross-process signal (flush buffers, quiz answered, etc.) would need
   another file or a proper IPC channel (pipe, socket, Redis).

2. **Knowledge graph and database can diverge.** The graph is the quiz engine's
   source of truth for memory scores; the database is the SM-2 engine's source
   of truth. External DB edits (e.g., DB browser) are not reflected in the graph
   until `sync_all_from_db()` runs.

3. **`track_loop()` itself has no tests.** The 145-test suite covers SM-2 logic,
   API endpoints, and NLP utilities, but the main loop and `_maybe_trigger_quiz()`
   are untested. These contain the most stateful logic (globals, session gating,
   inter-thread counters).

4. **Flask serves the built Vite bundle.** Frontend changes require a rebuild
   (`npm run build`) before they appear at `:5000`. The recommended dev mode
   (Vite at `:5173` + Flask at `:5000`) works but doubles process management.

---

## 4. Recommended Fix Priority

| Pri | Issue | Effort | Impact |
|---|---|---|---|
| 1 | [C-1] Privacy filter silently disabled on import error (resolved) | Low | Critical |
| 2 | [C-2] `started_at` not reset on session restart (resolved) | Low | High correctness |
| 3 | [H-2] Sparklines display random fabricated data (resolved) | Medium | User trust |
| 4 | [H-3] Intent feedback cooldown race condition (resolved) | Low | Data integrity |
| 5 | [C-4] Audio training data is entirely synthetic (resolved) | Medium | Model quality |
| 6 | [H-1] Duplicate SM-2 implementations (resolved) | Medium | Maintainability |
| 7 | [M-3] Duplicate quiz UI logic (resolved) | Low | Maintainability |
| 8 | [M-4] Date filter uses LIKE instead of range (resolved) | Low | Correctness |
| 9 | [M-5] Duplicate sensitive keyword lists (resolved) | Low | Correctness |
| 10 | [M-6] Lambda recalibration wrong success rate (resolved) | Low | Model accuracy |
| 11 | [M-7] BubbleGraph doesn't use edge data (resolved) | High | UX accuracy |
| 12 | [L-4] Toast dismiss state not persisted (resolved) | Low | UX polish |

---

## 5. What Was Explicitly NOT Flagged

The following patterns were investigated and found to be **intentional or acceptable**:

- `_LazySessionProxy` in `db/models.py` — correct lazy DB init pattern.
- `FKT_TEST_DB` env-var-must-be-set-before-import — documented in AGENTS.md, respected by tests.
- `concept_scheduler.py` `pass` in `__init__` — intentional; `SessionLocal` is the singleton.
- `db_path` backward-compat params in `ActivityMonitor` / `IntentValidator` — harmless, documented.
- `SECOND_REVIEW_INTERVAL_DAYS = 3` (not SM-2's canonical 6) — documented deliberate choice.
- `NO_AUTH=true` default — documented design decision for local dev; acceptable tradeoff.
- Audio `_audio_result_cache` module-level dict — intentional ring-buffer pattern for async cache.

---

*Investigation depth: all files in `tracker_app/tracking/`, `tracker_app/learning/`, `tracker_app/db/`,
`tracker_app/web/`, `tracker_app/web/frontend/src/`. Pending deeper review: `ReviewPage.tsx`,
`KnowledgeBasePage.tsx`, `AddConceptPage.tsx`, `webcam_module.py`, `keyword_extractor.py`,
full test suite.*
