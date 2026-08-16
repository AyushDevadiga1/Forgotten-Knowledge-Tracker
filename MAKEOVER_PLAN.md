# FKT Makeover Plan — Open Issues & Improvements

> **Ground rules:**
> - Only **open, unresolved** issues are listed. Resolved items have been removed.
> - Every finding cites the exact file and line(s) where it was confirmed.
> - Issues are evidence-based — no speculation, no assumptions.
> - This is a living document. Mark items `RESOLVED` with a short note when fixed.

---

## System Map (Quick Reference)

```
Screen   ──► OCR pipeline     ──► keywords dict
Mic      ──► audio pipeline   ──► {audio_label, confidence}
Webcam   ──► webcam_pipeline  ──► {attentiveness_score}
KB/Mouse ──► CLE module       ──► cle_score

All 4 ──► predict_intent() ──► intent_label

session_active AND intent_label in SESSION_ALLOWED_INTENTS:
  ──► ActivityMonitor.process_concepts()
      ──► ConceptScheduler.add_concept()
          ──► TrackedConcept (SQLite)
          ──► ConceptEncounter (SQLite)
          ──► sync_concept_to_graph()
              ──► knowledge_graph (networkx, in-memory + .pkl)

session_state.json ──► shared IPC toggle
```

---

## 1. CRITICAL — Must Fix Before Any Release

---

### [C-1] Authentication defaults to **off** with no startup warning

**RESOLVED — 9f8d24c: production requires SECRET_KEY; NO_AUTH=true now logged at startup.**

**File:** `web/app.py:38`, `web/auth.py:15`

Three compounding problems:

1. `SECRET_KEY` falls back to a hardcoded public string (`'dev-secret-key-change-in-production'`). Any deployment that doesn't explicitly set it in `.env` (common — `.env` is gitignored) has a predictable CSRF key. An attacker who reads the source can forge Flask-WTF CSRF tokens.
2. `NO_AUTH` defaults to `"true"` so `apply_auth_to_blueprint()` is called but immediately exits doing nothing. All JSON mutation endpoints (`POST /items`, `POST /reviews`, `POST /session/start`) are unprotected.
3. `api_bp` is explicitly CSRF-exempted (`csrf.exempt(api_bp)`), removing the last fallback.

```python
# web/app.py:38
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# web/auth.py:15
_NO_AUTH = os.getenv("NO_AUTH", "true").lower() == "true"  # default = auth off
```

**Fix:**
```python
secret = os.getenv('SECRET_KEY')
if not secret:
    if os.getenv('DEBUG', 'false').lower() == 'true':
        secret = 'dev-secret-key-change-in-production'
        logger.warning("Using insecure dev SECRET_KEY — set SECRET_KEY in .env")
    else:
        raise RuntimeError("SECRET_KEY must be set in production (DEBUG != true)")
app.config['SECRET_KEY'] = secret
```
Flip `NO_AUTH` default to `"false"` and log a startup warning when it is `"true"`.

---

### [C-2] Concurrent model retraining can corrupt `intent_classifier.pkl`

**RESOLVED — 274a363: retraining serialized under a lock; single subprocess.**

**File:** `web/api.py:108-121`

```python
count = FeedbackRepository.get_total_count(db)
if count > 0 and count % 50 == 0:   # no lock around this check
    t = threading.Thread(target=FeedbackService._retrain_from_feedback, ...)
    t.start()
```

`_retrain_from_feedback` spawns `subprocess.run(...)` which writes `intent_classifier.pkl`. If two HTTP requests arrive close together and both read the same `count % 50 == 0`, two subprocesses write to the same file simultaneously. One process writes a partial pickle while the other calls `pickle.load` in `_load_model`, producing a corrupt or truncated model.

**Fix:** Add a module-level `threading.Lock` guarding the `Thread.start()` call so only one retraining subprocess can run at a time.

---

## 2. HIGH — Correctness Bugs

---

### [H-1] `_idle_cycles` and `_last_quiz_time` are never reset between `track_loop()` restarts

**RESOLVED — 0254cdd: idle/cooldown state reset on track_loop restart.**

**File:** `tracking/loop.py:219`, `tracking/quiz_engine.py:23`

```python
_idle_cycles = 0                            # loop.py — module-level global
_last_quiz_time: Optional[datetime] = None  # quiz_engine.py — same
```

Both survive process restarts when `track_loop()` is re-called in the same process (test runs, signal-based reload). Stale values cause:
- 10 accumulated idle cycles → quiz fires in the **first cycle** of a fresh run before the `IDLE_CYCLES_REQUIRED = 12` threshold.
- A `_last_quiz_time` set before a crash → the 20-minute cooldown carries into the new session even though no quiz was seen.

**Fix:** Reset both at the top of `track_loop()` before the main loop. Expose a `reset_quiz_state()` helper for test isolation.

---

### [H-2] `record_quiz_result` spawns a throw-away `ConceptScheduler` on every call

**RESOLVED — 0254cdd: record_quiz_result reuses the scheduler singleton.**

**File:** `tracking/quiz_engine.py:159-161`

```python
def record_quiz_result(concept: str, was_correct: bool):
    scheduler = ConceptScheduler()  # fresh instance every call
    scheduler.schedule_next_review(concept, quality=quality)
```

`ConceptScheduler.__init__` is currently a no-op so the DB write works. But this bypasses the `ActivityMonitor.scheduler` singleton's in-memory state (session AWFC attention scores). If `__init__` ever gains state, divergence is silent and untestable without a live DB.

**Fix:** Pass the existing `ConceptScheduler` singleton through (or expose it as a module-level singleton) rather than constructing a throw-away instance.

---

### [H-3] `recalibrate_lambda` uses `first_seen` as the decay window — breaks for long-lived concepts

**RESOLVED — 33c17fe: lambda recalibrates over time since last review.**

**File:** `learning/memory_model.py:151-156`

```python
t_hours = (datetime.utcnow() - first_seen).total_seconds() / 3600.0
predicted_rate = math.exp(-current_lambda * t_hours) if t_hours > 0 else 1.0
adjustment = 0.05 * (predicted_rate - actual_success_rate)
```

For a concept 83 days old (`t_hours = 2000`) with `lambda = 0.1`:
`predicted_rate = exp(-200) ≈ 0`. The adjustment always pushes lambda up regardless of actual recall, eventually pinning it to `LAMBDA_CEIL = 0.50`. Long-lived concepts with good recall get their decay rate *increased* — the opposite of the intended personalisation.

**Fix:** Use `last_seen` (time since last review) as `t_hours`, not `first_seen`.

---

### [H-4] `webcam_pipeline` opens and closes the camera on every call — no persistent capture

**RESOLVED — 760d0c9: persistent camera handle.**

**File:** `tracking/webcam_module.py:79-99`, `104-167`

```python
def capture_frame():
    cap = cv2.VideoCapture(0)  # opens camera
    ...
    finally:
        cap.release()          # closes immediately

def webcam_pipeline(num_frames=3):
    for _ in range(num_frames):
        frame = capture_frame()  # opens + closes 3 times per cycle
```

`cv2.VideoCapture(0)` takes ~300 ms on most laptops. At 3 frames per cycle: 900 ms of pure I/O overhead before any pixel is processed. On many Windows drivers, repeated open/close also toggles the "camera in use" LED, which is alarming to users.

**Fix:** Hold a persistent `cap` in module state (opened once at first call, released on shutdown via `atexit`). `capture_frame()` becomes a simple `cap.read()`.

---

### [H-5] `_get_embed_model()` retries a failed load on every call — log spam storm

**RESOLVED — cd9751a: failed embed-model load cached by a sentinel.**

**File:** `tracking/knowledge_graph.py:32-43`

```python
def _get_embed_model():
    global _embed_model
    if _embed_model is None:           # re-entered after a failed load
        try:
            _embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"SentenceTransformer unavailable ({e})...")
            _embed_model = None        # stays None → next call re-enters
    return _embed_model
```

After a failed load `_embed_model` remains `None`, so every subsequent call re-attempts the import (may include a network download attempt) and logs another warning. Over a multi-hour session: hundreds of identical warnings. `_get_spacy_vectors` has the same problem.

**Fix:** Use a sentinel to distinguish "never tried" from "tried and failed":
```python
_EMBED_FAILED = object()
_embed_model = None   # None = untried; _EMBED_FAILED = load failed

def _get_embed_model():
    global _embed_model
    if _embed_model is _EMBED_FAILED:
        return None
    if _embed_model is None:
        try:
            _embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"SentenceTransformer unavailable: {e}. Will not retry.")
            _embed_model = _EMBED_FAILED
            return None
    return _embed_model
```

---

### [H-6] Knowledge graph grows without bound — no node limit, no TTL eviction

**RESOLVED — c264d08: node cap with low-memory eviction on save.**

**File:** `tracking/knowledge_graph.py` (entire module)

No cap on node count, no TTL, no low-relevance pruning. Each node stores a 384-dim float32 embedding (~1.5 KB). At 10,000 nodes: 15 MB just for embeddings plus NetworkX graph overhead. After months of use `_load_graph()` blocks the tracking thread for several seconds while deserializing the `.pkl`.

**Fix:** Add a `MAX_GRAPH_NODES = 5000` constant. When exceeded during `_save_graph()`, evict the nodes with the lowest `memory_score` that also have zero edges. This is a best-effort background operation — no correctness risk.

---

## 3. MEDIUM — Data Quality & Performance

---

### [M-1] `extract_keywords()` camelCase splitter discards the original compound form

**RESOLVED — 962a904: camelCase compound keyword retained.**

**File:** `tracking/ocr_module.py:298-321`

```python
parts = re.split(r'[_]', kw)
for p in final_parts:
    split_keywords[p] = max(score, split_keywords.get(p, 0.0))
# 'backPropagation' → only 'back' and 'propagation' are kept
```

The compound keyword (e.g. `backPropagation`) — scored highly by YAKE because it is a meaningful unit — is entirely replaced by its fragments. The original form is permanently discarded.

**Fix:** Add `split_keywords[kw.lower()] = score` before the split loop so the compound is always retained as a primary entry; parts are bonus entries.

---

### [M-2] `ActivityMonitor.prediction_buffer` is unbounded and never consumed

**RESOLVED — 2f70bcd: prediction_buffer is a bounded deque(100).**

**File:** `tracking/activity_monitor.py:68-72`

Populated every cycle (~every 5 s). After 8 hours: ~5,760 dicts. No code reads it — `get_accuracy_stats()` queries the DB directly.

**Fix:** Remove or replace with `collections.deque(maxlen=100)`.

---

### [M-3] `session_attention_scores` in `ActivityMonitor` is also unbounded

**RESOLVED — 2f70bcd: attention tracked as O(1) running mean.**

**File:** `tracking/activity_monitor.py:146, 238`

```python
self.session_attention_scores = []
...
self.session_attention_scores.append(attention_score)  # grows forever
```

`end_session()` only needs the average. A running Welford mean uses O(1) memory.

**Fix:** Replace the list with `_attention_sum: float = 0.0` and `_attention_count: int = 0`.

---

### [M-4] `get_graph()` called inside `extract_keywords()` inner loop triggers periodic DB sync on OCR thread

**RESOLVED — 4e7c067: graph preloaded and passed into extract_keywords.**

**File:** `tracking/ocr_module.py:338-343`

```python
G = get_graph()  # triggers _ensure_graph_loaded() → may run sync_db_to_graph()
for kw in list(kw_dict.keys()):
    if kw in G.nodes:
        kw_dict[kw] = min(1.0, kw_dict[kw] + 0.1)
```

When `DB_SYNC_INTERVAL_SECONDS` (60 s) has elapsed, `sync_db_to_graph()` runs a full DB query plus possible re-embedding of new concepts — all blocking the OCR worker thread.

**Fix:** Call `get_graph()` once at the top of `ocr_pipeline()`, pass the reference to `extract_keywords()`, and separate the node-boost lookup from the sync path.

---

### [M-5] `export_tracking_data()` crashes on a bare filename with no directory component

**RESOLVED — ff5f33d: parent dir guarded; bare filenames work.**

**File:** `tracking/activity_monitor.py:274`

```python
os.makedirs(os.path.dirname(output_file), exist_ok=True)
# "export.json" → dirname = '' → makedirs('') → FileNotFoundError
```

**Fix:**
```python
parent = os.path.dirname(output_file)
if parent:
    os.makedirs(parent, exist_ok=True)
```

---

### [M-6] Quiz cooldown is stamped **before** broadcast confirmation

**RESOLVED — 1ab7335: cooldown stamped only after successful broadcast.**

**File:** `tracking/quiz_engine.py:132`

```python
_last_quiz_time = datetime.utcnow()   # stamped at generation time
return {'concept': concept_name, ...}
# loop.py:251-254: broadcast_micro_quiz may silently fail
```

If the WebSocket broadcast fails (dashboard not running, client disconnected), the user never sees the quiz but the 20-minute cooldown is already consumed.

**Fix:** Move `_last_quiz_time = datetime.utcnow()` into `loop.py` — only set it after a successful `broadcast_micro_quiz` call.

---

### [M-7] `webcam_module` and `ocr_module` use `print()` instead of logger

**RESOLVED — 3ca101b: webcam/OCR messages routed through logger.**

**File:** `tracking/webcam_module.py:57, 95`, `tracking/ocr_module.py` (≥15 call sites)

```python
print(f"Error calculating EAR: {e}")   # webcam_module.py:57
print(f"Error capturing frame: {e}")   # webcam_module.py:95
```

Privacy-critical messages (`[PRIVACY] Skipped sensitive window: ...`) and errors never reach the rotating log file when running as a background service. They are discarded silently.

**Fix:** Replace all `print(...)` in both files with `logger.warning/debug(...)`.

---

### [M-8] `_is_subsumed_single_word` does a leading-wildcard `LIKE '%x%'` full-table scan

**RESOLVED — c8c14a5: subsuming phrases preloaded once, no LIKE scan.**

**File:** `learning/concept_promotion.py:89-100`

```python
others = db.query(TrackedConcept).filter(
    TrackedConcept.concept.like(f"%{concept}%"),  # index unusable
).all()
```

SQLite cannot use any index for `LIKE '%...'` (leading wildcard). This is a full-table scan per promoted concept. With thousands of tracked concepts this is the dominant cost of every `backfill_items()` run.

**Fix:** Load all multi-word concept strings into a Python set before the promotion loop and perform membership checks in memory.

---

### [M-9] `_load_graph()` acquires the reentrant lock inside a caller that already holds it — undocumented implicit contract

**RESOLVED — 94a4940: renamed _load_graph_locked, contract documented.**

**File:** `tracking/knowledge_graph.py:73-108`

```python
def _ensure_graph_loaded():
    with _graph_lock:            # outer acquire
        if not _load_graph():   # _load_graph also acquires
            ...

def _load_graph() -> bool:
    with _graph_lock:            # inner re-acquire (RLock — no deadlock)
        knowledge_graph.clear()
```

The `RLock` prevents a deadlock, but `_load_graph()` silently requires either "always called with the lock held" or "always called without it". A future caller without the lock creates a data race. The contract is not documented.

**Fix:** Remove `with _graph_lock:` from `_load_graph()` and rename it `_load_graph_locked()` to make the requirement explicit.

---

### [M-10] YAKE extractor parameters appear configurable per-call but are silently ignored after first init

**RESOLVED — c940e8b: fixed singleton config documented.**

**File:** `tracking/keyword_extractor.py:32-51`, `tracking/ocr_module.py:267`

```python
def _get_yake(language="en", max_ngram=2, top_n=20):
    global _yake_extractor
    if _yake_extractor is None:
        _yake_extractor = yake.KeywordExtractor(... top=top_n ...)
    return _yake_extractor   # always returns top=20 singleton
```

`ocr_module.py` calls `extract_keywords(text, top_n=10)`. YAKE extracts 20 internally and the final `[:top_n]` slice returns 10 — wasteful but not incorrect. The dangerous part: passing different `language` or `max_ngram` values silently returns the old singleton with the wrong settings.

**Fix:** Remove per-call parameters from `_get_yake()` and document the singleton's fixed parameters.

---

## 4. LOW / Style / Dead Code

---

### [L-1] `db_module.py` log message names tables that do not exist

**RESOLVED — ed12cdb: log lists dynamically built ORM tables.**

**File:** `db/db_module.py:19`

```python
logger.info("SQLAlchemy tables constructed: sessions, multi_modal_logs, memory_decay, etc.")
```

`multi_modal_logs` and `memory_decay` are not ORM table names. Misleads anyone debugging schema.

**Fix:** `f"SQLAlchemy tables constructed: {[t.name for t in Base.metadata.sorted_tables]}"`

---

### [L-2] `get_learning_stats()` loads every `LearningItem` row into memory for a `len()` call

**RESOLVED — 424dba5: count via get_total_count, no full load.**

**File:** `learning/learning_tracker.py:162`

```python
total_count = len(LearningRepository.get_all_items(db))  # loads all rows
```

**Fix:** `db.query(func.count(LearningItem.id)).scalar() or 0` — `get_total_count()` already exists in the repository and does exactly this.

---

### [L-3] `NO_AUTH=true` default leaves auth silently inert with no log

**RESOLVED — 9f8d24c: startup warning logged when auth is inert.**

**File:** `web/auth.py:15`, `web/app.py:48`

`apply_auth_to_blueprint(api_bp)` is called, but `_NO_AUTH` defaults to `True` so it immediately returns. No warning is emitted. The call site looks like auth is active when it isn't.

**Fix:** Emit a `logger.warning("API authentication is DISABLED (NO_AUTH=true)")` at startup when `_NO_AUTH` is True.

---

### [L-4] `webcam_pipeline` returns hard-coded `face_count: 1 if ear_values else 0`

**RESOLVED — 70ac5cf: true face count reported.**

**File:** `tracking/webcam_module.py:164`

```python
"face_count": 1 if ear_values else 0,  # boolean cast, not actual count
```

Consumers expecting the actual number of faces detected (e.g. multi-person detection extensions) get wrong data.

**Fix:** Track `faces_detected = sum(len(r.multi_face_landmarks or []) for r in results_list)` and return the true count.

---

### [L-5] `concept_promotion._answer_for()` opens a separate DB session from its caller — 3 total sessions for one promotion

**RESOLVED — 644a345: caller session reused, two sessions fewer.**

**File:** `learning/concept_promotion.py:54-68`

`_answer_for()` opens `SessionLocal`. `promote_concept_to_deck()` also opens `SessionLocal`. `LearningTracker().add_learning_item()` opens a third. Three round-trip sessions for a single promotion.

**Fix:** Pass `db: Session` as a parameter to `_answer_for()` and `_difficulty_for()`.

---

### [L-6] `CURATED_EXCEPTIONS` is hardcoded — no user-editable mechanism

**RESOLVED — 148bd4a: DATA_DIR/curated_exceptions.txt with fallback.**

**File:** `learning/concept_promotion.py:31-34`

```python
CURATED_EXCEPTIONS = frozenset({'big-o notation', 'ebbinghaus forgetting curve'})
```

Users cannot extend this list without editing source code.

**Fix:** Load from `DATA_DIR/curated_exceptions.txt` at startup, falling back to the hardcoded set.

---

## 5. Feature Improvements (Recommended Additions)

These are not bugs but high-value improvements based on structural gaps found during the audit.

---

### [F-1] No rate limiting on any API endpoint

**RESOLVED — 1eb5619: flask-limiter wired, 60/min default, TESTING exemption.**

**File:** `web/api.py` (all routes)

A browser extension bug or rogue tab can call `POST /api/v1/reviews` in a tight loop and flood the DB. No per-endpoint rate limit exists.

**Recommendation:** Add `flask-limiter` with `default_limits = ["60 per minute"]` across all blueprint routes.

---

### [F-2] No input sanitisation on `browser_ingest` title field

**RESOLVED — fabbba0: C0/C1 control chars stripped from title.**

**File:** `web/api.py:618-619`

```python
title = str(data.get('title', ''))[:200]   # truncated but not sanitised
```

Stored in `ConceptEncounter.context_snippet`. A malicious or buggy extension can inject HTML or control characters that reach the UI.

**Recommendation:** Strip control characters and validate the field is printable Unicode before storing.

---

### [F-3] `session_state.json` has no cross-process OS lock — unsafe with multiple Flask workers

**File:** `tracking/session_state.py`

The threading `_lock` is within-process only. Running Flask under Gunicorn with `--workers 2` allows two worker processes to write `session_state.json` simultaneously. `Path.replace()` is atomic for the rename, but both processes can be inside `json.dump(tmp, ...)` at the same time.

**Recommendation:** Replace the JSON toggle with a single-row SQLite table. SQLite WAL mode handles concurrent writes correctly and removes the IPC file entirely.

---

### [F-4] `FeedbackTrainingSample` rows accumulate indefinitely

**RESOLVED — 3f90840: used_in_training column + 90-day prune.**

**File:** `web/api.py:88-96`, `db/models.py`

Every intent correction is stored forever. Over years this table holds millions of rows. The training script uses all of them, making retraining progressively slower.

**Recommendation:** Add a `used_in_training` boolean column. After each training run, mark used samples. Add a periodic cleanup that deletes `used_in_training=True` rows older than 90 days.

---

### [F-5] EAR thresholds are hardcoded — no per-user calibration

**File:** `tracking/webcam_module.py:67-74`

```python
if avg_ear < 0.2:          # one-size-fits-all thresholds
    return max(0.0, (avg_ear / 0.2) * 40.0)
elif avg_ear > 0.35:
    return 100.0
```

EAR varies significantly between users (glasses, eye shape, lighting conditions). Incorrect attention scores corrupt AWFC memory weights for all tracked concepts.

**Recommendation:** Add a 30-second calibration step at session start. Measure the user's personal EAR baseline (eyes-open mean and eyes-partially-closed floor) and persist it in `session_state.json` for the session.

---

### [F-6] No API endpoint to force a knowledge graph resync

**RESOLVED — 1aaa78b: POST /api/v1/graph/sync force resync.**

**File:** `tracking/knowledge_graph.py`, `web/api.py`

External DB edits (DB Browser for SQLite, direct SQL scripts) are not reflected in the in-memory graph for up to 60 seconds. Micro-quiz memory scores can be stale.

**Recommendation:** Add `POST /api/v1/graph/sync` that calls `sync_db_to_graph(force=True)` and returns the updated node/edge count. Surface it in the dashboard Settings tab.

---

### [F-7] Zero tests for `track_loop()` and `_maybe_trigger_quiz()`

**RESOLVED — 607125d: track_loop + quiz-trigger integration coverage.**

**File:** `tracking/loop.py` (entirely untested)

The tracking loop and quiz trigger are the most stateful, most bug-prone code paths. Bugs H-1 and M-6 above would have been caught by a basic integration test.

**Recommendation:**
- Test `track_loop()` with a `stop_event` that fires after 2 iterations, using mocked pipeline functions.
- Test `_maybe_trigger_quiz()` directly, asserting `_idle_cycles` resets when session is inactive.
- Test quiz cooldown: inject `_last_quiz_time = now - timedelta(minutes=19)` and assert no quiz fires.

---

## 6. Priority Matrix

| Pri | ID | Issue | Effort | Impact |
|---|---|---|---|---|
| 1 | F-3 | `session_state.json` unsafe with multiple workers | Medium | Reliability |
| 2 | F-5 | EAR thresholds hardcoded - no per-user calibration | Low | UX |

> Every other item in this plan (C-1..C-2, H-1..H-6, M-1..M-10, L-1..L-6,
> F-1, F-2, F-4, F-6, F-7) is RESOLVED and committed — see the RESOLVED
> note on each section for the resolving commit.

---

*Investigation covers: `tracking/` (all 10 files), `learning/` (all 5 files), `db/` (all files), `web/api.py`, `web/app.py`, `web/auth.py`, `web/realtime.py`, `config.py`, `main.py`. Frontend `web/frontend/src/` reviewed for API contract only — component-level TSX audit is separate.*
