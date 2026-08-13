# FKT-F-002 — run_migrations() never wired into app startup; stale DBs crash with "no such column"

- ID: FKT-F-002
- STATUS: VERIFIED
- SEVERITY: MEDIUM (HIGH for upgrade scenario)
- SCOPE: tracker_app.db.models ↔ tracker_app.db.migrations ↔ app startup
- LOCATION:
  - tracker_app/db/migrations.py:160-230 (runner), only invoked from `__main__` (migrations.py:271) and tools/launcher.py `migrate` subcommand
  - tracker_app/web/app.py:29 and tracker_app/tracking/loop.py:274 — startup calls `init_all_databases()` (create_all only)
  - tracker_app/db/db_module.py:15-23 — `init_db()` = `Base.metadata.create_all` (never ALTERs existing tables)
  - Columns only added by migrations, referenced by consumers: intent_predictions.prompted_at (007, models.py:184), window_title (008, models.py:185), tracked_concepts.repetitions (009, models.py:240), review_count/correct_count (010, models.py:241-242), attention_at_encoding/lambda_personalised (002, models.py:245-246)
- CLAIM: An existing DB that predates any migration-only column fails at runtime on first ORM write (e.g. api.py:426-434 updates prompted_at; concept_scheduler.py:189-204 writes repetitions/review_count) because no startup path applies migrations.
- EXPECTED: Startup applies idempotent migrations (design intent per migrations.py:32-34) or schema convergence is otherwise guaranteed before model use.
- OBSERVED: Runtime probe: simulated old-schema intent_predictions (no prompted_at/window_title), inserted via model without create_all → `OperationalError: table intent_predictions has no column named prompted_at`. Live data/sessions.db is fully migrated (schema_migrations 001-010), so no current failure — latent upgrade hazard. CI runs `python -m tracker_app.db.migrations` explicitly, confirming the only automated application is a manual/CI step.
- EVIDENCE: hunter probes (runtime-hunter H2, logic-hunter H2, contract-hunter H3) + greps of startup call sites.
- REPRODUCTION: CONFIRMED (bug-reproducer; see REPRODUCTION/STATUS below)
- ROOT_CAUSE: (tentative) schema-evolution mechanism (migrations) decoupled from startup path.
- RELATED_PATTERN: P-002
- AFFECTED_INSTANCES: (pending)
- FIX: `init_all_databases()` (tracker_app/db/db_module.py) now calls `run_migrations(db_path=get_db_path())` after `init_db()` and logs the applied/skipped/failed counts; `init_db()` itself remains create_all-only. All startup paths (web/app.py:29, tracking/loop.py:274, learning_tracker.py:309, concept_scheduler.py:302, tools) funnel through `init_all_databases()`, so every runtime entry converges stale schemas. Implemented in OpenSpec change "run-migrations-at-startup".
- OPENSPEC_CHANGE: run-migrations-at-startup
- REGRESSION_TEST: tracker_app/tests/test_migrations_at_startup.py — (1) stale-schema DB (raw sqlite3 DDL intent_predictions without prompted_at/window_title, per reproducer probe 1) after `init_all_databases()`: schema_migrations has all 10 entries, ORM IntentPrediction insert (incl. migration-only columns) succeeds, and the api.py:426-434 prompted_at claim UPDATE returns rowcount 1; (2) already-migrated DB: a second `init_all_databases()` is a no-op — `run_migrations(db_path=...)` reports applied=0, skipped=10. Both use throwaway tmp_path DBs (FKT_TEST_DB + `_engine`/`_SessionLocal` reset, engine disposed after).
- VERIFICATION: `venv\Scripts\python.exe -m pytest tracker_app/tests/test_migrations_at_startup.py -v` → 2 passed; full `venv\Scripts\python.exe -m pytest tracker_app/tests -q` → 244 passed (baseline 242 + 2 new, all green). Guard: tracker_app/data/sessions.db size (765952 bytes) and mtime (2026-08-12 07:10:15) identical before and after the test run; live DB fully migrated (001-010) so the import-time `init_all_databases()` in test_api.py is a skipped-only no-op.


---

## REPRODUCTION/STATUS — bug-reproducer evidence gate

- CLASSIFICATION: CONFIRMED
- DATE: 2026-08-13
- REPRODUCER: bug-reproducer (read-only on repo source; all DBs under C:\Users\hp\AppData\Local\Temp\opencode)
- VENV PYTHON: C:\Users\hp\Desktop\FKT\venv\Scripts\python.exe (fresh subprocess per probe; FKT_TEST_DB set before any tracker_app import)

### Probe 1 — old-schema DB crashes on ORM write (simulated pre-migration DB)
Script: C:\Users\hp\AppData\Local\Temp\opencode\f002_probe1.py
DB: C:\Users\hp\AppData\Local\Temp\opencode\f002_old.db
Setup: raw sqlite3 DDL `CREATE TABLE intent_predictions (id, timestamp, predicted_intent, confidence, context_keywords, user_feedback, actual_intent, feedback_timestamp)` — no prompted_at / window_title. Then ORM `SessionLocal().add(IntentPrediction(...)); commit()` via tracker_app.db.models.
OBSERVED:
```
PROBE1 RESULT: OperationalError: (sqlite3.OperationalError) table intent_predictions has no column named prompted_at
[SQL: INSERT INTO intent_predictions (timestamp, predicted_intent, confidence, context_keywords, user_feedback, actual_intent, feedback_timestamp, prompted_at, window_title) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
```
EXPECTED (per candidate): schema converges or a clear migration step runs before model use. OBSERVED: hard OperationalError on first ORM write.

### Probe 2 — startup does NOT apply migrations
Script: C:\Users\hp\AppData\Local\Temp\opencode\f002_probe2.py
DB: C:\Users\hp\AppData\Local\Temp\opencode\f002_startup.db (fresh, empty)
Setup: `import tracker_app.web.app` (the real production startup path; executes `init_all_databases()` at import, web/app.py:29). Import SUCCEEDED (flask/socketio/api/learning imports all fine).
OBSERVED:
```
tables after startup init: ['concept_encounters', 'daily_summary', 'feedback_training_samples', 'intent_accuracy', 'intent_predictions', 'learning_items', 'memory_decay', 'metrics', 'multi_modal_logs', 'review_history', 'sessions', 'tracked_concepts', 'tracking_sessions']
schema_migrations present: False
PROBE2 RESULT: NO schema_migrations table after startup init -> migrations NOT applied on the startup path
```
Conclusion: `init_all_databases()` = `Base.metadata.create_all` only (db_module.py:15-23); it never runs `run_migrations`. The migration runner is invoked ONLY from migrations.py:271 (`__main__`), launcher.py:46-51 (manual `migrate` CLI subcommand), and .github/workflows/ci.yml:39-40 (explicit CI step). No startup path (web/app.py:29, tracking/loop.py:274) calls it.

### Probe 3 — positive control: migration runner fixes the same DB
Script: C:\Users\hp\AppData\Local\Temp\opencode\f002_probe3.py
DB: C:\Users\hp\AppData\Local\Temp\opencode\f002_old.db (same old-schema DDL as probe 1, recreated)
Setup: `venv\Scripts\python.exe -m tracker_app.db.migrations` with FKT_TEST_DB set (fresh subprocess), then identical ORM insert.
OBSERVED:
```
Done: 10 applied, 0 skipped, 0 failed
All migrations successful.
schema_migrations applied: ['001_schema_migrations', ..., '010_tracked_review_counts']
intent_predictions columns now: [..., 'prompted_at', 'window_title']
PROBE3 RESULT: INSERT SUCCEEDED after migrations (expected positive control)
```
Conclusion: the runner converges the same DB such that the identical write succeeds — the failure mode is precisely the absence of any migration call on the startup path.

### Probe 4 — exact api.py consumer path fails on old-schema DB
Script: C:\Users\hp\AppData\Local\Temp\opencode\f002_probe4.py
DB: C:\Users\hp\AppData\Local\Temp\opencode\f002_old2.db (old-schema intent_predictions with one seeded row)
Setup: replicated web/api.py:426-434 `update(IntentPrediction).where(prompted_at.is_(None), user_feedback.is_(None)).values(prompted_at=now)` plus the preceding ORM row read (api.py:407).
OBSERVED:
```
PROBE4 RESULT: OperationalError: (sqlite3.OperationalError) no such column: intent_predictions.prompted_at
[SQL: SELECT intent_predictions.id ..., intent_predictions.prompted_at AS intent_predictions_prompted_at, intent_predictions.window_title ... FROM intent_predictions LIMIT ? OFFSET ?]
```
Note: failure occurs even on the ORM SELECT (api.py reads row.window_title at api.py:445 and the repo SELECT references prompted_at) — any ORM access to IntentPrediction against a pre-007/008 DB crashes.

### Verdict
- Candidate claim "An existing DB that predates any migration-only column fails at runtime on first ORM write because no startup path applies migrations" is REPRODUCED with concrete evidence on every assertion point (probe 1, 2, 4) and the positive control (probe 3).
- Not exercised: live data/sessions.db (left untouched; read-only rule) and concept_scheduler.py:189-222 write path (same mechanism — ORM columns repetitions/review_count against a pre-009/010 DB would fail identically; not separately probed because probe 1/4 already demonstrate the mechanism).
- Remaining risk (design decision, not defect evidence): whether auto-migration at startup is desired vs. documenting a mandatory `python -m tracker_app.db.migrations` step.
