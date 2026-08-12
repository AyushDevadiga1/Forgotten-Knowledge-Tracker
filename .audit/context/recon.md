# FKT Recon — v2 (recon-only run, 2026-08-12)

## Mode & constraints

- RECON-ONLY run. No application code, tests, OpenSpec artifacts, AGENTS.md, or configuration were modified. Only this `.audit/` context artifact was written.

## Git state (evidence: `git status`, `git log`, `git branch -avv`)

- HEAD: `343ee62` "chore: checkpoint before audit architecture migration"; branch `main`, **ahead of `origin/main` by 4** (origin at `d914a67`). Local commits not pushed:
  - `a0dd9e2` fix(audio): syllabic-modulation heuristics replace synthetic GaussianNB
  - `16f467c` fix(api,graph): truthy booleans, trend boundary, graph staleness, route crash guards
  - `95de59a` chore: initialize agentic development workflow (OpenSpec integration scaffolding: `.opencode/`, `.agent/`, `.hermes/`, `.github/` opsx skills/workflows; `openspec/config.yaml`; `adversarial-debugger.md`, `debug-hunt.md`)
  - `343ee62` chore: checkpoint before audit architecture migration
- Working tree:
  - `README.md` **modified (tracked, uncommitted)** — content replaced with "FKT Adversarial Audit v2" package description; original project README is only in git history.
  - Untracked: `.audit/` (scaffold), `.opencode/agents/*` (v2 agent set incl. `audit-orchestrator` + 10 read-only/hunter agents), `.opencode/commands/audit.md`, `.opencode/skills/audit-*/` (9 skills), `AGENTS.v2.md`, `MANIFEST.txt`, `MIGRATION.md`.
  - `AGENTS.md` **unmodified** — old monolithic debugging protocol still the active project rules.
- Earlier `git show 34362ee` failure was a mistyped abbreviation; full hash `343ee62...` resolves fine.

## Previous audit (v1) — shipped locally, not yet on origin

- `a0dd9e2` — `tracking/audio_module.py` + `tests/test_audio_heuristics.py`: fake "trained" classifier (ADR-002 synthetic MFCCs) replaced by envelope-power syllabic-band detection with silence→tonal→syllabic→ambient decision path.
- `16f467c` — 7 files, +353/−25, 14 regression tests:
  - `web/api.py`: `_parse_bool_flag` strict booleans (`/intent/feedback`, `/quiz/answer` — `bool('false') is True` bug); `record_review`/`create_item` `.strip()` on JSON numbers → str-coercion + None→400.
  - `db/repository.py`: `get_trend_analysis` binds datetime object instead of isoformat string (space-vs-T separator boundary bug).
  - `tracking/knowledge_graph.py`: `_ensure_graph_loaded` loaded-flag; missing concepts added on first contact; 60 s `sync_db_to_graph` resync; prints→logger.
- Last known green: **236 passed** at commit time. Current `.pytest_cache` shows **239 node IDs**, `lastfailed: {}` (empty) — consistent with a later green full run; re-run to confirm before any v2 cycle claims.

## Architecture map (evidence: module inventory, route/def greps)

- Entry: `tracker_app/main.py` → `tracking/loop.py` (`track_loop`, `warm_up_all_pipelines`, `_maybe_trigger_quiz`, `_safe_run`). Web: `tracker_app/web/app.py` (Flask app + SPA catch-all), blueprint `api_bp` in `web/api.py` (**727 lines**, unmodified in tree), `realtime.py` (SocketIO), `auth.py`.
- API surface — 26 routes (`api_bp`): `/items` GET/POST, `/items/backfill`, `/items/due`, `/items/<id>` GET/DELETE, `/concepts/<concept>` DELETE, `/intent/predictions` DELETE, `/tracking/history` DELETE, `/reviews` POST, `/stats`, `/stats/trend`, `/intent/recent`, `/intent/feedback` POST, `/graph/stats|gaps|drift/<concept>|concept/<concept>`, `/quiz/current`, `/quiz/answer` POST, `/ingest` POST, `/session/status|start|stop`, `/health`.
- Tracking modules: `session_state.py` (JSON session gating), `privacy_filter.py` (sensitive text/window gates, redaction, keyword filter), `keyword_extractor.py` (YAKE+spacy), `intent_module.py` (rule-based predict; model loader), `cle_module.py`, `audio_module.py`, `webcam_module.py`, `ocr_module.py`, `activity_monitor.py` (session logging, daily summary, `get_trend_analysis`), `quiz_engine.py`, `knowledge_graph.py` (embed model, load/save, `add_concepts`, `sync_concept_to_graph`, `sync_db_to_graph`, drift, gaps).
- Learning: `sm2_memory_model.py`, `memory_model.py`, `learning_tracker.py`, `concept_scheduler.py` (sensitive/PII gate), `concept_promotion.py`, `text_quality_validator.py`.
- DB: `db/models.py` (SQLAlchemy: LearningItem, ReviewHistory, IntentPrediction, IntentAccuracy, TrackingSession, DailySummary, TrackedConcept, ConceptEncounter, SystemSession, MultiModalLog, MemoryDecay, Metric, FeedbackTrainingSample; lazy engine/session proxies), `db/repository.py` (LearningRepository, TrackingRepository, FeedbackRepository), `db/migrations.py` (idempotent, `run_migrations`), `db/db_module.py`.
- Data: `tracker_app/data/` — `sessions.db`, `knowledge_graph.pkl`, `session_state.json`, backups `sessions.backup-*.db`, exports.
- Frontend: `tracker_app/web/frontend/` (package.json present, TS/SPA).
- Docs: `architecture/high_level/`, `architecture/low_level/` (LLD, ERD, DFD, sequence diagrams), `architecture/adr/` (ADR-001 SQLite, ADR-002 Heuristics-over-ML, ADR-003 Reinstate-RandomForest-Intent). `README.md` (working-tree version = audit-package description; original README only in git).

## Verification commands (evidence: `.github/workflows/ci.yml`, `requirements.txt`)

- CI backend: `python -m tracker_app.db.migrations` then `pytest tracker_app/tests/ -v --tb=short`; Python 3.11; **reduced deps** (flask, flask-wtf, flask-cors, flask-socketio, python-dotenv, sqlalchemy, numpy, networkx, scikit-learn, spacy, yake, pytest + `python -m spacy download en_core_web_sm`). Heavy runtime deps (tesseract/opencv/mediapipe/librosa/psutil/pynput) are absent on CI — modules must degrade gracefully.
- Local: `venv\Scripts\python.exe -m pytest tracker_app/tests -q` (venv is CPython 3.13; full `requirements.txt` includes heavy deps + pywin32 on Windows).
- CI frontend: `npm ci`; `npx tsc --noEmit`; `npm run build` in `tracker_app/web/frontend`.
- No Python lint/type-check configured in CI.

## OpenSpec state

- `openspec/config.yaml` exists (schema: spec-driven; githubCopilot.cloudAgent). `openspec/specs/` and `openspec/changes/` are **empty** (0 files; `changes/archive` empty). → No OpenSpec intent/change baseline currently; repo code + tests + ADRs are the intent evidence for v2.

## .audit state

- Scaffold complete: `README.md`, `SCHEMA.md`, `context/`, `evidence/`, `findings/`, `patterns/`, `verification/` (each with README). **No findings recorded yet.** This file is the first context artifact.

## Migration status (in progress — per `MIGRATION.md`)

- Add step: v2 agents/skills/commands + `.audit/` + `AGENTS.v2.md` — copied (untracked) but not committed.
- Replace step: `AGENTS.md` merge from `AGENTS.v2.md` — **not done** (AGENTS.md untouched).
- Retire step: `.opencode/agents/adversarial-debugger.md` after `/audit` verified — **not done**.
- First run step: start with narrow scope, inspect `recon.md` + first candidate records, then repository-wide.
- Note: tracked `README.md` already overwritten with the audit-package description (uncommitted); original content preserved in git history.

## High-risk subsystem triage for v2 (grounded in v1 findings)

1. `web/api.py` — 26-route contract surface; v1 bugs clustered here (bool parsing, None/crash guards, date boundary). Contract + logic focus.
2. `tracking/knowledge_graph.py` — process-cached graph + 60 s periodic resync; cross-process staleness with DB; drift/gap math.
3. `db/repository.py` + `db/models.py` — datetime/boundary handling (v1 `get_trend_analysis` pattern), lazy session lifecycle, schema-vs-models drift.
4. `tracking/loop.py` + `quiz_engine.py` + `session_state.py` — cross-module state flow and quiz triggering.
5. `db/migrations.py` — idempotency vs ORM models.
6. Frontend TS ↔ `api.py` JSON contract mismatches (tsc/build only type-check frontend; no cross-contract check).

## Uncertainties / open questions

- Pytest cache shows 239 node IDs vs 236 at v1 commit — re-run full suite to establish current green baseline.
- CI state on origin/main unknown (last upstream CI ran on `d914a67`; 4 local commits unpushed).
- `Measure-Object -Line` undercounts lines in `api.py` (reported 622; actual 727 via `.Count`) — use `.Count` for line counting.
