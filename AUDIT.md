# FKT Autonomous Audit Log

Loop: `issues/PROMPT.md` (Ralph's Loop Variant). One task per iteration; findings appended below in structured tables. Evidence over speculation; no secrets logged.

## Phase 1 — Reconnaissance

### 1.1 Data-input map (internal model)

| Input class | Source | Path / config | Notes |
|---|---|---|---|
| Screen OCR | `mss` screenshot + Tesseract via pytesseract | `tracker_app/tracking/` | SCREENSHOT_INTERVAL=20s default; OCR_MIN_WORD_CONFIDENCE=30 floor |
| Audio | sounddevice + librosa classification | `tracker_app/tracking/audio_module.py` | AUDIO_INTERVAL=15s |
| Webcam | MediaPipe FaceMesh → EAR | `tracker_app/tracking/webcam_module.py` | WEBCAM_INTERVAL=45s; ALLOW_WEBCAM gate |
| Keystrokes | pynput → CLE | `tracker_app/tracking/` | Inter-key timing entropy, backspace rate etc. |
| Foreground window | pywin32 win32gui (Windows-only) | `tracker_app/tracking/` | not on Linux CI |
| Focused browser tab | pywinauto Windows UIA (Windows-only) | `tracker_app/tracking/focused_tab.py` | title+URL ground truth; overrides OCR bias |
| Browser ingest | `tracker_app/web/extension/` | POST `/api/v1/ingest` | content-script → Flask API |
| HTTP API | 9 blueprints | `tracker_app/web/routes/*.py` under `/api/v1` | graph, health, ingest, intent, items, quiz, session, stats, telemetry |
| Realtime | Flask-Socket.IO | `tracker_app/web/realtime.py` | dashboard push |
| SQLite DB | SQLAlchemy | `tracker_app/data/sessions.db` (DATABASE_URL) | FKT_TEST_DB redirects test writes |
| Knowledge graph | JSON | `tracker_app/data/knowledge_graph.json` | |
| Logs | file handler | `tracker_app/logs/tracker.log` | |
| Env config | `.env` (gitignored) | `tracker_app/config.py` → load_dotenv | SECRET_KEY, API_KEY, NO_AUTH, TESSERACT_PATH, intervals, SESSION_ALLOWED_INTENTS, CALIBRATION_* |
| Model artifact | pickle | `tracker_app/models/intent_classifier.pkl` (generated) | retrain: `python -m tracker_app.scripts.train_models_from_logs` |
| Golden data | label JSON + PNG | `data/golden/` + `tools/golden_eval.py` | ground truth for intent tests (0.93 target) |

### 1.2 Findings

| ID | Subject | Severity | Location | Finding | Evidence | Status |
|---|---|---|---|---|---|---|
| FKT-001 | Docker default secret | LOW | docker-compose.yml:7 | `SECRET_KEY=${SECRET_KEY:-dev-secret-key-change-in-production}` — the containerised (production-ish) path silently boot wraps a well-known public secret; `config.py` only auto-rotates when len<32, and this default is 34 chars, so it is used verbatim | docker-compose.yml L7; tracker_app/config.py L18-21 | OPEN |

## Phase 2.1 — Entry points, API routes, controllers (unvalidated inputs / boundary errors)

| ID | Subject | Severity | Location | Finding | Evidence | Status |
|---|---|---|---|---|---|---|
| FKT-002 | EAR calibration duration | MED | web/routes/session.py:119-126 | `duration_seconds` from JSON body is not range-checked: negative -> silent fallback result (no 400), huge value (e.g. 2147483647) -> `calibrate_ear` blocks the request thread for that duration in a tight webcam loop; inconsistent with the bounded `days`/`limit`/`min_frequency` params elsewhere | session.py:123 `int(req["duration_seconds"])`; webcam_module.py:84 `while time.time()-start < duration_seconds` | CONFIRMED |
| FKT-003 | Unbounded `answer` + untyped `tags` | LOW | web/routes/items.py:46-88 | `create_item` caps `question` at QUESTION_MAX_LENGTH but never bounds `answer` (multi-MB bodies reach the DB) and passes `tags` unchecked to `json.dumps` (non-list -> wrong shape); boundary validation inconsistent with ingest caps | items.py:54-68; learning_tracker.py:81 `json.dumps(tags or [])` | CONFIRMED |
| FKT-004 | Raw exception leak in API errors | LOW | web/routes/*.py (items, stats, graph, quiz, session, ingest, telemetry) | `str(e)` returned verbatim in error bodies (paths, SQL fragments, model details) and auth is OFF by default (`API_KEY` empty -> `check_api_key` no-op), so internal strings are readable without credentials | shared.py:31-42; e.g. items.py:133-134, stats.py:25 | CONFIRMED |
| FKT-005 | `/api/v1/quiz/current` always 500 | HIGH | web/routes/quiz.py:17-25 | Route imports `generate_quiz` from `tracker_app.tracking.quiz_engine`, but the module only defines `generate_micro_quiz(graph)` — every request raises ImportError -> deterministic 500; the frontend QuizPage consumes this via `api.getQuiz` | quiz.py:18 vs quiz_engine.py:130 `def generate_micro_quiz(graph)`; reproduced: `hasattr(quiz_engine,'generate_quiz')` -> False; frontend/src/api.ts:188 | CONFIRMED |

## Phase 2.2 — Authentication layers, session handling, token verification

| ID | Subject | Severity | Location | Finding | Evidence | Status |
|---|---|---|---|---|---|---|
| FKT-006 | Auth-enabled consumers send no key | MED | web/frontend/src/api.ts:8-10; web/frontend/src/components/MicroQuizModal.tsx:17; web/extension/background.js:29-38 | The documented production step (DEPLOYMENT.md: `API_KEY` + `NO_AUTH=false`) locks out every client: the frontend HTTP client sends only Content-Type, Socket.IO connects with `io()` (no `api_key` param), and the extension fetch omits `X-API-Key`; all would be rejected 401/403 (or WS-rejected), so enabling auth breaks the dashboard + extension entirely | apiFetch headers:8-10; `io()` MicroQuizModal.tsx:17; background.js headers:31; _ws_auth_ok realtime.py:23-27 | CONFIRMED |
| FKT-007 | Non-constant-time key compare | LOW | web/shared.py:40 | `check_api_key` compares the supplied key with `!=` while the parallel implementation `auth.py:25` uses `hmac.compare_digest`; on a loopback-only interface the practical risk is minimal, but the two auth paths disagree on timing-safe comparison | shared.py:40 `provided != api_key` vs auth.py:25 `hmac.compare_digest` | CONFIRMED |
| FKT-008 | CSRF-able state mutations when auth off (default) | LOW | web/app.py:72 (`csrf.exempt(bp)`); web/routes/session.py, items.py, graph.py | With API auth off (the default) and all blueprints CSRF-exempt, a hostile page can cross-origin trigger form-POST-able mutations — `/session/start`, `/session/stop`, `/session/calibrate`, `/triage/<id>/approve|reject`, `/items/<id>/archive|unarchive`, `/items/backfill`, `/graph/sync` — with no preflight and no CSRF token. JSON-only endpoints resist this because mis-typed bodies 400 | app.py:72; session.py:83-105; items.py:150-169, 228-249 | CONFIRMED |

## Phase 2.3 - Data-processing functions (memory leaks / type-safety / unhandled crashes)

| ID | Subject | Severity | Location | Finding | Evidence | Status |
|---|---|---|---|---|---|---|
| FKT-009 | EAR calibration never applied to attention | MED | tracking/loop.py:171; tracking/webcam_module.py:210-272 | '_get_attention_score' reads webcam_result.get("_raw_ear_values", []) to feed per-user calibrated thresholds into compute_attention_score, but webcam_pipeline never includes that key - its returned dicts contain only attentiveness_score/face_count/frames_processed/status (both the mediapipe_unavailable return and the frame-processed return). The raw-ear key appears exactly once in the repo (the read). So the calibration branch (loop.py:172-177) is dead code: the per-user EAR baseline captured by the blocking per-session calibrate_ear is stored but never used; attention always uses hardcoded 0.2/0.35 defaults via attentiveness_score. Amplifier: the call at loop.py:497 is the only pipeline step outside _safe_run and is unguarded - if a future producer ever added the raw-ear key with non-float values, the whole loop would die. | grep for the raw-ear key -> single hit (loop.py:171); runtime repro: webcam_pipeline(num_frames=0) keys = set(attentiveness_score, face_count, frames_processed, status); _get_attention_score(True, {attentiveness_score:42.0 ...}, cle, ear_calibration={personal_ear_low:0.18, personal_ear_high:0.30}) -> 44.4 == default-branch math (0.7*42 + 0.3*50), proving calibrated branch not reached | CONFIRMED |


## Phase 3.1 - DB query files / storage managers (state mutations / query vulnerabilities)

| ID | Subject | Severity | Location | Finding | Evidence | Status |
|---|---|---|---|---|---|---|
| FKT-010 | DB flush logger dumps raw captured fields to the file log | MED | db/models.py:128-135; main.py:55-60; tracking/loop.py:526-535 | The global `after_flush` SQLAlchemy hook logs `obj.__dict__` at INFO for every inserted/updated/deleted row. Focused-tab URLs are persisted untruncated (loop passes the raw URL; `focused_tab.py` performs no sensitive-content prune, only the window-title gate), so a URL carrying sensitive query strings (bank statement, search terms, SSN-like params) is echoed verbatim into `tracker.log` on every write. No other layer in the pipeline stores raw capture text unfiltered; this hook bypasses the sanitisation that privacy_filter applies to OCR content, and the log file is unencrypted and unrestricted on the local disk. Runs for every write from the tracking loop and the API (event is registered on the `Session` class). | Reproduced: commit a `MultiModalLog` with focused_tab = {url: https://chase.com/account?ssn=123-45-6789...}; DB_Models INFO emits "INSERTED [MultiModalLog]: {..., 'focused_tab': '{...ssn=123-45-6789...}'}" verbatim. main.py logs at INFO via FileHandler to tracker.log | CONFIRMED |


## Phase 3.2 - Env vars / secrets managers / config loading

| ID | Subject | Severity | Location | Finding | Evidence | Status |
|---|---|---|---|---|---|---|
| FKT-011 | Default setup boots into enforced auth with an unrecoverable auto-minted key | MED | tracker_app/config.py:23-27; `.env.example:7-8` | `.env.example` ships `API_KEY=` + `NO_AUTH=false`, and config.py auto-mints an ephemeral `secrets.token_hex(24)` whenever API_KEY is empty and NO_AUTH != true. The documented copy-the-example flow therefore boots with auth ENFORCED under a 48-char key that is never printed, never persisted, and unrecoverable - the operator cannot learn it, so the dashboard/extension are locked out (interacts with FKT-006) even though the user never intended to enable auth. The mint was clearly designed for "operator enabled auth but left key empty", but because NO_AUTH defaults to false it fires on the default documented setup. Test `test_auth_dev_mode.py` only asserts the key is not written into `.env`, not that enforcement stays off. | Subprocess repro: env {API_KEY:"", NO_AUTH:"false"} -> after `import tracker_app.config` os.environ["API_KEY"] = 48-char minted key and (NO_AUTH false + key set) -> shared.py check_api_key now enforces X-API-Key on every call | CONFIRMED |
| FKT-012 | Unvalidated env int/bool parsing crashes startup at import time | LOW | tracker_app/config.py:93-96,129-144; `.env.example` | `int(os.environ.get("TRACK_INTERVAL", 5))` and friends run at module import; a malformed value (e.g. `TRACK_INTERVAL=abc`) raises a bare ValueError that aborts the whole app before `validate_config()` (which only checks positivity, post-import) can report it. `NO_AUTH` parsing accepts only the lowercase `"true"` - `TRUE/True/1/yes` are silently treated as disabled, flipping auth on unintentionally. Same root cause: loose, unvalidated env parsing with no clamping/fallback. | Subprocess repro: env {TRACK_INTERVAL:"abc"} -> `import tracker_app.config` -> ValueError: invalid literal for int() with base 10 | CONFIRMED |
