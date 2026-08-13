# Adversarial Verification — FKT Bug-Fix Audit (F-001…F-007)

Date: 2026-08-13
Method: independent post-fix adversarial verification (read-only on repo; probes in
C:\Users\hp\AppData\Local\Temp\opencode under FKT_TEST_DB; real DB opened mode=ro only)

## Full test suite
- venv\Scripts\python.exe -m pytest tracker_app/tests -q
- RESULT: 256 passed, 0 failed (817 warnings; deprecation warnings only)
- Targeted new regression files: 11 passed (test_db_path_resolution, test_migrations_at_startup,
  test_datetime_storage_format, test_duplicate_feedback_index); 44 passed (test_learning_tracker,
  test_concept_scheduler, test_feedback_pipeline)
- Real DB after my suite run: size 765,952 / mtime 2026-08-13 19:01:36 — IDENTICAL to pre-run
  snapshot => my verification run wrote nothing to production DB.

## Per-fix verdicts

### F-001 db path resolution + session binding — PASS (one sibling noted)
- Env-driven engine/session works in fresh subprocess (baseline probe).
- Self-rebind (models.SessionLocal = proxy): identity guard -> no recursion, sessions work.
- Rebind to non-callable -> loud TypeError (config error surfaces; better than pre-fix crash).
- del models.SessionLocal -> captured proxy falls back to global; module-scope importers
  (concept_promotion) now delegate to the rebound session (core purpose verified by insert probe).
- Thread-safety: 4 threads x 300 iterations with concurrent rebinding -> no errors.
- FKT_TEST_DB="" (config error): get_db_path() returns ''; get_engine() -> sqlite:/// temp-file DB;
  init_all_databases with mid-process "" degrades to throwaway temp DB (silent, benign).
- Engine cache after env change remains sticky (documented limitation; monotonic per process).
- SIBLING: run_migrations() default `db_path or DB_PATH` still reads import-time-frozen DB_PATH
  (only affects CLI/__main__ callers; init_all_databases passes get_db_path()).

### F-002 migrations at startup — PASS with significant concern
- Idempotent: repeated init_all_databases -> applied=0 skipped=12.
- Partial pre-seeded schema_migrations (001-005) -> remaining 7 applied, all 12 present.
- Bad migration appended: create_all intact, failure logged, not marked applied, retried next run.
- WAL concurrency with open ORM connection: no errors.
- CONCERN (mechanism demonstrated): web/app.py init_all_databases runs at IMPORT time on the
  env-bound DB. test_api.py:19, test_feedback_pipeline.py:25, test_intent_toast_cooldown.py:23
  import web.app at module scope WITHOUT FKT_TEST_DB -> pytest collection mutates production
  data/sessions.db. Evidence: real DB 19:01:36 mtime, 001-012 applied, T-rows normalized to 0,
  legacy index dropped — 011/012 data-mutating migrations were applied to production DB by a
  process running after this fix landed. Any FUTURE pending migration will be applied to the real
  DB at test collection. Benign today (converged); latent hazard for future migrations.

### F-003 last_review_date — PASS
- sm2 + leitner review branches persist non-null last_review_date; survives reload.
- Baseline None -> no crash; _dict_to_sm2item(None) -> None; DB NULL handled.
- _row_to_dict with plain dict raises on row.id — same as pre-fix; all real callers pass ORM rows.

### F-004 datetime storage format — PASS
- substr edge probes: no-micro / with-micro 'T' normalized and parseable; tz-offset row normalized
  (parses as aware datetime; SQL ordering still correct); truncated/garbage 'T' rows transformed
  identically-badly as before (neutral; no writer produces them); space/date-only rows untouched.
- Second run idempotent (test). populate.py end-to-end writes space format in all 8 columns.
- Real DB: 0 T-format rows remaining in all 8 checked columns.

### F-005 feature-vector JSON contract — PASS
- features=[] -> context_keywords '[]' (trainer gate: skipped += 1, no crash, json.loads+len==6).
- features=[1,2] / context_keywords=None -> sample skipped, user feedback still recorded.
- Non-ASCII title + 6-vector: sample created, vector round-trips; window_title stored verbatim.

### F-006 drop duplicate feedback index — PASS
- create_all-only DB: run_migrations applied=12 failed=0; legacy index absent before/after;
  ORM insert after drop works (012 uses IF EXISTS).
- Both-indexes DB converges (regression test). Real DB: only ORM index remains.

### F-007 source labeling — PASS (minor notes)
- /ingest passes browser_extension (persisted); OCR path defaults 'ocr'; explicit source verbatim.
- No validation: source=None -> NULL, 123 -> '123', '' -> '' (SQLite TEXT affinity). No consumer
  reads source; pre-existing free-text String column contract unchanged.

## Real DB read-only baseline (verified pre- and post-verification, unchanged)
- schema_migrations: 001-012 applied. feedback_training_samples indexes: only
  ix_feedback_training_samples_timestamp. T-rows: 0 in tracked_concepts.next_review/first_seen/
  last_seen, sessions.start_ts/end_ts, multi_modal_logs.timestamp, memory_decay.last_seen_ts/
  updated_at. Row counts: tracked_concepts=395, intent_predictions=993, feedback_training_samples=1,
  learning_items=59, concept_encounters=5, sessions=100, multi_modal_logs=200, memory_decay=54.
  learning_items.last_review_date non-null = 0 (expected; fix writes only on new reviews).
- No data loss observed; counts match pre-fix values.

## Overall
ALL 7 FIXES: PASS. No regression found in suite or probes.
Watch items: (1) F-002 collection-time migration side effect on real DB during pytest;
(2) F-001 engine cache stickiness + run_migrations frozen DB_PATH default (CLI only).
