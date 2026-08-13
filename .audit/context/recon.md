# FKT Recon - v3 refresh (2026-08-13) - DB subsystem cycle (tracker_app/db/models.py)

## Mode & constraints

- RECON-ONLY refresh. No application code, tests, OpenSpec artifacts, AGENTS.md, or configuration modified. Only `.audit/context/recon.md` was overwritten.
- Audit cycle scope: `tracker_app/db/models.py` (DB subsystem). Observations for hunters below are marked as observations, not confirmed bugs.

## Git state (evidence: `git status`, `git log --oneline -12`, `git branch -avv`)

- HEAD: `bd26cad` "docs(map): add interactive function dependency map with regenerate tooling"; branch `main`, **up to date with `origin/main`** (`origin/main` == `bd26cad`, `origin/HEAD -> origin/main`). No local unpushed commits.
- Last 12 commits (newest first): `bd26cad` docs(map), `27b1a28` docs(readme), `bdc8194` chore(openspec) require OpenSpec change for every modification, `e95c308` feat(opencode) capture behavior-changing fixes as OpenSpec changes, `6282f28` docs(opencode) adversarial audit v2 migration guide, `ad7856d` chore(opencode) permissions for audit agents, `5e3ebab` feat(audit) durable audit memory structure, `70cc8fc` feat(opencode) on-demand audit skills, `76da049` feat(opencode) adversarial audit agent pipeline, `343ee62` chore checkpoint before audit architecture migration, `95de59a` chore initialize agentic development workflow, `16f467c` fix(api,graph) v1 bugfix batch.
- Working tree: **clean** except one untracked directory `fkt-audit-v3/` (contains `.audit/`, `.opencode/`, `AGENTS.v3.md`, `MANIFEST.txt`, `MIGRATION.md`, `README.md` - a newer audit-tooling snapshot, not committed). No modified tracked files.
- `.audit/`, `.opencode/`, `openspec/`, `AGENTS.v2.md` are now **tracked** (committed in the `95de59a..bd26cad` series). This corrects the stale v2 recon which listed them as untracked.
- `AGENTS.md` is **gitignored** (`.gitignore:72`) and NOT tracked; current content is the "Project Operating Rules" file (v2 merge). `AGENTS.v2.md` (tracked) differs from `AGENTS.md`.
- `.pytest_cache`: 239 node IDs, `lastfailed` is `{}` (empty) - consistent with a passed full run, not re-run during this recon.

## Architecture map (evidence: module inventory, greps, reads)

- Entry: `tracker_app/main.py`; web: `tracker_app/web/app.py` (Flask + SPA catch-all), blueprint `api_bp` in `web/api.py` (**727 lines**, confirmed), `realtime.py` (SocketIO), `auth.py`. Tracking: `tracking/loop.py` (track_loop, warm_up_all_pipelines, _maybe_trigger_quiz, _safe_run).
- DB subsystem (`tracker_app/db/`, 4 source files + `__init__.py`):
  - `db/models.py` (339 lines) - SQLAlchemy ORM, 13 models, lazy engine/session factories, `after_flush` logging.
  - `db/repository.py` (308 lines) - DAO layer: `LearningRepository` (item CRUD, get_items_due, get_stats, get_learning_today, get_review_trend, search_items, get_items), `TrackingRepository` (log_session, log_intent_prediction, update_intent_accuracy, get_accuracy_stats, get_daily_summary, get_trend_analysis), `FeedbackRepository` (log_feedback_sample, get_all_samples, get_total_count). Static methods taking a Session; commits happen inside methods.
  - `db/migrations.py` (280 lines) - no-Alembic idempotent runner: `ensure_base_schema` (create_all from current models, for fresh DBs), `MIGRATIONS` registry 001-010, `run_migrations` (guards ADD COLUMN via `_column_exists`), `print_status`, `__main__` with `--status`.
  - `db/db_module.py` (26 lines) - `ensure_db_directory`, `init_db` (`Base.metadata.create_all(bind=get_engine())`), `init_all_databases`; `__main__` calls init.
- Config: `tracker_app/config.py` - `DB_PATH = os.environ.get('FKT_TEST_DB', str(DATA_DIR / "sessions.db"))` where `DATA_DIR = tracker_app/data`. `PROJECT_ROOT` = `tracker_app/` dir.
- Data: `tracker_app/data/` (sessions.db, knowledge_graph.pkl, session_state.json, backups, exports).

## DB models (evidence: db/models.py)

13 models, class -> table:
1. LearningItem -> learning_items
2. ReviewHistory -> review_history
3. IntentPrediction -> intent_predictions
4. IntentAccuracy -> intent_accuracy
5. TrackingSession -> tracking_sessions
6. DailySummary -> daily_summary
7. TrackedConcept -> tracked_concepts
8. ConceptEncounter -> concept_encounters
9. SystemSession -> sessions
10. MultiModalLog -> multi_modal_logs
11. MemoryDecay -> memory_decay
12. Metric -> metrics
13. FeedbackTrainingSample -> feedback_training_samples

Mechanics of models.py:
- Lazy engine: `get_engine()` creates engine on first call (sqlite:///{DB_PATH}, check_same_thread=False, pool_pre_ping, pool_recycle=3600) and installs a connect event setting `PRAGMA foreign_keys=ON`, `journal_mode=WAL`, `synchronous=NORMAL`. `get_session_local()` creates sessionmaker (autocommit=False, autoflush=False). Module-level `SessionLocal` and `engine` are lazy proxies (`_LazySessionProxy`, `_LazyEngineProxy`). `get_db()` yields a session, closes but never commits.
- `@event.listens_for(Session, "after_flush")` -> `receive_after_flush` logs `obj.__dict__` for session.new/dirty/deleted at INFO to logger `"DB_Models"` (no handler configured; relies on root propagation).

## Primary consumers of db.models (evidence: grep across tracker_app/)

Production code (file:line):
- db/repository.py:10 (LearningItem, ReviewHistory, TrackingSession, IntentPrediction, IntentAccuracy, FeedbackTrainingSample, TrackedConcept)
- db/db_module.py:5 (get_engine, Base, get_db)
- db/migrations.py:23 (Base, inside ensure_base_schema)
- learning/concept_scheduler.py:9 (TrackedConcept, ConceptEncounter, SessionLocal)
- learning/learning_tracker.py:11 (LearningItem, ReviewHistory)
- learning/concept_promotion.py:16 (SessionLocal, TrackedConcept, ConceptEncounter); :120 (LearningItem, import inside function)
- tracking/knowledge_graph.py:158, 249, 261, 308 (SessionLocal, TrackedConcept); :371 (SessionLocal, ConceptEncounter) - all imports inside functions
- tracking/activity_monitor.py:12 (SessionLocal, IntentPrediction, TrackingSession)
- web/api.py:62 (SessionLocal, FeedbackTrainingSample); :91 (SessionLocal); :252 (SessionLocal, TrackedConcept); :273, :297 (multiple); :403 (SessionLocal, IntentPrediction); :505 (SessionLocal, TrackedConcept); :707 (SessionLocal) - all imports inside functions
- scripts/train_models_from_logs.py:158 (SessionLocal, import inside function)

Tests: tests/test_intent_toast_cooldown.py, test_graph_memory_sync.py, test_graph_drift_gaps.py, test_feedback_pipeline.py, test_concept_scheduler.py, test_new_system.py, test_concept_promotion.py, test_learning_tracker.py, test_api.py (all import Base + models directly).

## Verification commands (evidence: .github/workflows/ci.yml, venv probe)

- CI backend (ubuntu, Python 3.11, setup-python v5): `pip install flask flask-wtf flask-cors flask-socketio python-dotenv sqlalchemy numpy networkx scikit-learn spacy yake pytest`; `python -m spacy download en_core_web_sm`; `python -m tracker_app.db.migrations` (env PYTHONIOENCODING=utf-8); `pytest tracker_app/tests/ -v --tb=short`. Heavy runtime deps (tesseract/opencv/mediapipe/librosa/psutil/pynput) absent on CI - modules must degrade gracefully.
- CI frontend (Node 20, working-directory tracker_app/web/frontend): `npm ci`; `npx tsc --noEmit`; `npm run build`.
- No Python lint/type-check configured in CI.
- Local venv: `C:\Users\hp\Desktop\FKT\venv\Scripts\python.exe` = **CPython 3.13.7**. Full suite: `venv\Scripts\python.exe -m pytest tracker_app/tests -q`. `db/__pycache__` contains both cpython-311 and cpython-313 pyc files (both interpreters have imported the db package).

## OpenSpec state

- `openspec/config.yaml` exists. `openspec/specs/` **exists but is empty** (0 files).
- `openspec/changes/` has 3 active changes (each with .openspec.yaml + proposal.md + tasks.md, tasks all checked): `adopt-openspec-for-all-changes`, `interactive-function-dependency-map`, `plain-language-readme`. `changes/archive` empty.
- Commit `bdc8194` requires an OpenSpec change for every modification; `e95c308` requires behavior-changing fixes be captured as OpenSpec changes. No main specs yet (specs/ empty) - deltas not synced.

## .audit state

- `.audit/` is tracked. Files: `README.md`, `SCHEMA.md`, `context/README.md`, `context/recon.md` (this file), `evidence/README.md`, `findings/README.md`, `patterns/README.md`, `verification/README.md`. **No findings recorded yet.**
- Untracked `fkt-audit-v3/` at repo root carries a newer audit-tooling snapshot (incl. `AGENTS.v3.md`) - awareness item, not repo state.

## High-risk triage - DB subsystem (observations for hunters, NOT confirmed bugs)

1. Models <-> migrations drift, both directions:
   - Migration 005 adds `last_review_date TEXT` to `learning_items`, but the `LearningItem` ORM model does **not** declare it. Code only touches it defensively: `learning_tracker._row_to_dict` uses `getattr(row, 'last_review_date', None)` (always None through the ORM); `sm2_memory_model.SM2Item.last_review_date` is a plain non-ORM attribute. The DB column exists but is neither mapped nor read/written via the ORM. Observation: orphan column + defensive reads that silently return None.
   - Only 005 shows model-less columns today; conversely any future model column without a migration won't exist on legacy DBs (`create_all` never ALTERs). `ensure_base_schema` runs create_all before migrations, and ADD COLUMN is guarded by `_column_exists`, so ordering is safe for current set.
2. Lazy engine, eager config: `get_engine()` re-imports `tracker_app.config` to "re-read" `DB_PATH`, but config.py evaluates `DB_PATH` at module import time (line 32) and Python caches modules - so the re-read returns the same value if `tracker_app.config` was imported first. models.py line 13 imports config at module level, so importing models eagerly pins DB_PATH. The engine is lazy; the config value is not. Tests must set `FKT_TEST_DB` before any `tracker_app.config` import. db_module.py and migrations.py also read DB_PATH at module level. Observation: lazy-engine docstring (lines 18-23) overstates the guarantee.
3. after_flush logger: fires for every Session in every process (incl. tests), logs `obj.__dict__` (includes `_sa_instance_state`) at INFO for new/dirty/deleted, including sensitive fields (window_title, context_snippet, question/answer). Logger "DB_Models" has no handler. Observation: noise, PII-in-logs surface, per-flush cost on the ~5 s intent-prediction hot loop.
4. `LearningItem.id` is a String PK with **no default** - id must be supplied by every creation path (web/api.py create_item, concept_promotion:120, quiz flows). No ORM-side generation; NULL/duplicate string ids fail at flush/commit. Observation: audit every creation site.
5. Write-orphaned tables: grep for `Metric(`, `SystemSession(`, `DailySummary(`, `MultiModalLog(`, `MemoryDecay(` across all `*.py` finds **only** the class definitions in models.py - no construction sites in tracker_app/. They are only read/deleted: `/tracking/history` DELETE (web/api.py:291-319) deletes ConceptEncounter, TrackingSession, MultiModalLog, MemoryDecay, Metric, DailySummary, IntentPrediction, IntentAccuracy, FeedbackTrainingSample (keeps learning_items). Two session tables exist: `tracking_sessions` (written by activity_monitor) vs `sessions` (SystemSession, never written in tracker_app/). Observation: check whether writers live outside tracker_app/ (scripts/) or whether tables are dead weight.
6. FK/cascade pattern: ReviewHistory.item_id FK -> learning_items.id (String PK, ondelete=CASCADE, passive_deletes=True, cascade delete-orphan); ConceptEncounter -> tracked_concepts same pattern. Engine sets `PRAGMA foreign_keys=ON` per connect; migrations.py also sets it on its raw connection. String PK vs Integer FK value matching is a SQLite-affinity nuance worth verifying on actual delete paths.
7. Session lifecycle: `get_db()` never commits (callers must); repository methods commit internally; sessionmaker has `autoflush=False` - implicit-flush-before-query assumptions could surface ordering issues (e.g., add-then-query-due in the same session).
8. Known-good boundary code (v1 fixes live here): `get_trend_analysis` binds datetime objects (comment explains space-vs-T string-compare bug); `get_review_trend` aggregates per-day from stored timestamps with quality >= 3 correctness threshold; `get_learning_today` uses start-of-day/now boundaries. These are the established patterns to compare new findings against.
9. Concurrency: WAL + check_same_thread=False + pool_pre_ping; Flask + SocketIO threads share SessionLocal. No evidence of explicit locking around cross-process access (knowledge_graph resync is a known v1-stability area, not this cycle's scope).

## Uncertainties / open questions

- Full pytest suite not executed during this recon (read-only). `.pytest_cache` (239 node IDs, lastfailed {}) implies a later green run than the 236-passed baseline at v1 commit; confirm with `venv\Scripts\python.exe -m pytest tracker_app/tests -q`.
- CI status of origin/main unknown (HEAD == origin/main; no run performed here).
- Whether orphan tables (metrics, sessions, multi_modal_logs, daily_summary, memory_decay) are written by code outside tracker_app/ (grep covered tracker_app/ only).
- Whether any path writes `last_review_date` via raw SQL (no evidence in tracker_app/).
- `fkt-audit-v3/` (untracked) suggests a v3 tooling migration may be intended; not reflected in tracked repo state.
