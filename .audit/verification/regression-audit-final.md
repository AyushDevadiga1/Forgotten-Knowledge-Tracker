# Regression Audit — Final Verification Record (FKT-F-001..FKT-F-007)

- Auditor: regression-auditor (big-pickle)
- Date: 2026-08-13
- Environment: Windows, venv `venv\Scripts\python.exe` (Python 3.13.7 local; CI Python 3.11)
- Mode: read-only on product code and tests; only write is this record under `.audit\verification\`.

## 1. Test evidence

### 1a. Full backend suite (exact command)
```
venv\Scripts\python.exe -m pytest tracker_app/tests -q
```
RESULT: **256 passed, 0 failed, 817 warnings in 70.39s** — warnings are exclusively
`datetime.datetime.utcnow()` DeprecationWarnings (pre-existing, tracked as a remaining risk).

### 1b. New/updated regression test files together
```
venv\Scripts\python.exe -m pytest tracker_app/tests/test_db_path_resolution.py
  tracker_app/tests/test_migrations_at_startup.py tracker_app/tests/test_learning_tracker.py
  tracker_app/tests/test_datetime_storage_format.py tracker_app/tests/test_feedback_pipeline.py
  tracker_app/tests/test_duplicate_feedback_index.py tracker_app/tests/test_concept_scheduler.py -q
```
RESULT: **55 passed, 0 failed, 313 warnings in 67.52s.**

Regression tests prove intended behavior (spot-checked each):
- F-001 test_db_path_resolution.py (4): env read at call time (get_db_path/get_engine), module-scope
  SessionLocal importer honors rebind (row lands in rebound DB, absent from env DB), engine proxy honors
  rebind.
- F-002 test_migrations_at_startup.py (2): stale pre-007/008 schema converges via init_all_databases
  (migrations 001-012 recorded, ORM insert + api.py prompted_at claim UPDATE rowcount=1); idempotency
  (second run applied=0 skipped=12).
- F-003 test_learning_tracker.py (+2): sm2 and leitner reviews persist non-null last_review_date that
  survives a fresh-session reload.
- F-004 test_datetime_storage_format.py (3): 'T'-seeded row excluded at same-day boundary then included
  after run_migrations (future row stays excluded); 011 idempotent; populate.py emits space format in all
  8 columns.
- F-005 test_feedback_pipeline.py TestFeatureVectorJsonContract (4+): fallback stores "[]"; non-JSON /
  JSON-non-list / wrong-length vectors record feedback but skip sample; 6-vector positive control
  round-trips.
- F-006 test_duplicate_feedback_index.py (2): fresh migrated DB has exactly one index
  (ix_feedback_training_samples_timestamp); both-indexes DB converges and second run is a no-op; real DB
  guarded (size/mtime) by the tests themselves.
- F-007 test_concept_scheduler.py (+2): explicit source=browser_extension persisted; default remains 'ocr'.
- Minor: test_migrations_at_startup.py intro docstring still says "11 entries / skipped=11" while the
  assertion constant is 12 — stale prose only, assertions are correct.

## 2. CI parity (throwaway FKT_TEST_DB)

CI (`.github/workflows/ci.yml`) backend steps: `python -m tracker_app.db.migrations` then
`pytest tracker_app/tests/ -v --tb=short` on Python 3.11; frontend job = `tsc --noEmit` + `npm run build`.

Replicated against throwaway DB:
```
$env:FKT_TEST_DB='C:\Users\hp\AppData\Local\Temp\opencode\regression-audit-ci.db'
venv\Scripts\python.exe -m tracker_app.db.migrations
```
RESULT: **12 applied, 0 skipped, 0 failed** (001..012 all [OK]; 011/012 data-mutating migrations present).

```
$env:FKT_TEST_DB='...\regression-audit-ci.db'; venv\Scripts\python.exe -m pytest tracker_app/tests -q --tb=short
```
RESULT: **255 passed, 1 failed**. The single failure is pre-existing and environment-dependent:
`test_config.py::test_db_path_is_string` asserts `"sessions.db" in config.DB_PATH`, which is only true when
FKT_TEST_DB is unset (CI does not set it → CI passes; the default-env full run above confirms 256/256).
This test file is NOT part of the diff. Not a regression.

Python 3.11 vs 3.13 risk scan of changed files: no 3.12/3.13-only syntax (no match/case, PEP 695, `datetime.UTC`);
`datetime.utcnow()` is deprecated in 3.12+ (warning, not error, in 3.13) and not deprecated in 3.11 — no CI
risk from the changes. No Python lint/type-check tooling exists in the repo (no pyproject.toml/.flake8/ruff/mypy/
pre-commit); CI defines none, so no lint gate was skipped — there is nothing to run.

## 3. OpenSpec changes (7)

All 7 have `.openspec.yaml` with `skip_specs: true`; proposal.md and tasks.md present; **0 unchecked tasks**
in every tasks.md; `openspec validate --all` → **10 passed, 0 failed**; `openspec doctor` → root ok.

`openspec status --change <name> --json`:
| change | proposal | specs | design | tasks | isComplete |
|---|---|---|---|---|---|
| fix-db-path-resolution-and-session-binding | done | skipped | **ready (missing)** | done | false |
| run-migrations-at-startup | done | skipped | done | done | true |
| map-learning-item-last-review-date | done | skipped | **ready (missing)** | done | false |
| normalize-datetime-storage-format | done | skipped | done | done | true |
| enforce-feature-vector-json-contract | done | skipped | **ready (missing)** | done | false |
| drop-duplicate-feedback-index | done | skipped | **ready (missing)** | done | false |
| label-concept-encounter-source | done | skipped | **ready (missing)** | done | false |

Per the audit's stated criteria (proposal/tasks done, specs skipped) artifacts are complete; but the
spec-driven schema treats `design.md` as a required artifact, so `openspec status` reports
`isPlanningComplete: false` for 5 of the 7 (design neither done nor skipped). GAP: 5 changes lack design.md.

## 4. Evidence completeness (findings FKT-F-001..FKT-F-007)

| finding | STATUS | OPENSPEC_CHANGE | REPRODUCTION | FIX | REGRESSION_TEST | VERIFICATION |
|---|---|---|---|---|---|---|
| F-001 | CONFIRMED | fix-db-path-resolution-and-session-binding | CONFIRMED (probes) | IMPLEMENTED | ADDED (4 tests) | filled |
| F-002 | CONFIRMED | run-migrations-at-startup | CONFIRMED (4 probes) | IMPLEMENTED | ADDED (2 tests) | filled |
| F-003 | CONFIRMED | map-learning-item-last-review-date | CONFIRMED (6 commands) | IMPLEMENTED | ADDED (2 tests) | filled |
| F-004 | CONFIRMED | normalize-datetime-storage-format | CONFIRMED (7 stages) | IMPLEMENTED | ADDED (3 tests) | filled |
| F-005 | CONFIRMED | enforce-feature-vector-json-contract | CONFIRMED (3 repros) | IMPLEMENTED | ADDED (4 tests) | filled |
| F-006 | **CANDIDATE (header)** | drop-duplicate-feedback-index | CONFIRMED | IMPLEMENTED | ADDED (2 tests) | filled |
| F-007 | CONFIRMED | label-concept-encounter-source | CONFIRMED (4 probes) | IMPLEMENTED | ADDED (2 tests) | filled |

GAP: FKT-F-006 header `STATUS: CANDIDATE` is stale — its own REPRODUCTION section classifies CONFIRMED and
fix+verification are complete; the header should be CONFIRMED/FIXED/VERIFIED. (Not fixed per instructions.)
Minor: F-001 `RELATED_PATTERN`/`AFFECTED_INSTANCES` still "(pending pattern-miner)" although
`.audit/patterns/P-001..P-007` exist; not in the required-field list.

## 5. Real-DB safety (read-only, `file:...?mode=ro`)

`tracker_app\data\sessions.db` current state:
- schema_migrations: **001..012 present** (incl. 011_datetime_storage_format, 012_drop_duplicate_feedback_index)
- tracked_concepts: **395 rows**, **0 'T'-format next_review** (T-rows also 0 in first_seen/last_seen)
- feedback_training_samples indexes: **only `ix_feedback_training_samples_timestamp`** (legacy dropped)
- learning_items: **has `last_review_date` column** (59 rows, 0 non-null — expected: fix writes on new reviews only)
- other row counts: intent_predictions 993, feedback_training_samples 1, concept_encounters 5, sessions 100,
  multi_modal_logs 200, memory_decay 54; T-format rows 0 in all 8 checked DateTime columns.

Integrity: sessions.db size 765952 / mtime 2026-08-13T19:01:36 identical before and after all runs.
`sessions.db-shm` (32768 B, 19:47:31) and `sessions.db-wal` (0 B) sidecars appeared during pytest runs —
WAL is empty ⇒ zero content mutation; the sidecars are evidence of the collection-time open (risk below).

## 6. Migration runner CLI

```
$env:FKT_TEST_DB='C:\Users\hp\AppData\Local\Temp\opencode\regression-audit-ci.db'
venv\Scripts\python.exe -m tracker_app.db.migrations --status
```
RESULT: **12 applied, 0 pending** — 001..012 all `[OK] applied`.

## 7. Frontend / TS scope

`git status --porcelain -- '*.ts' '*.tsx' '*.js' '*.jsx' '*.vue' '*.json'` → **empty**. No frontend/TS files
changed ⇒ CI `frontend-build` job (tsc + npm build) is unaffected by this work. The full diff is 14 files:
12 backend Python sources/tests + openspec changes + .audit artifacts (see git status).

## Remaining risks / watch items
1. **Collection-time migration side effect (F-002)**: test_api.py / test_feedback_pipeline.py /
   test_intent_toast_cooldown.py import web.app at module scope without FKT_TEST_DB → `init_all_databases()`
   (now migration-running) executes against the REAL data/sessions.db during pytest collection. No-op today
   (converged, evidenced by empty WAL), but any FUTURE pending migration will be applied to the production DB
   by any test run that imports web.app. -shm/-wal sidecar files were created by this cycle's runs.
2. **F-001 engine-cache stickiness**: web/app.py still creates the engine at import time via
   init_all_databases(); a mid-process FKT_TEST_DB change cannot rebind an already-created engine (documented
   design decision). Sibling: run_migrations()'s default `db_path or DB_PATH` still reads the frozen import-time
   constant (CLI/__main__ callers only).
3. **datetime.utcnow() deprecation**: 817 suite warnings; deprecated since 3.12, scheduled for removal — not a
   CI risk on 3.11 today, but a real migration item before Python 3.14.
4. **OpenSpec design artifacts**: 5/7 changes lack design.md (`openspec status` isPlanningComplete: false).

## Verdict: **READY**
All 7 fixes verified: full suite 256/256 (default env) and 55/55 targeted regression tests green; CI-parity
commands pass against a throwaway DB (12 migrations applied; pytest 255/256, the single failure being the
pre-existing env-sensitive test_config.py assertion that CI cannot hit); real DB untouched (content) with all
expected post-fix state (001-012, 0 T-rows, single feedback index, last_review_date column present);
migration --status lists 001-012; no frontend files changed. Gaps found are record/documentation-only
(F-006 stale CANDIDATE header; missing design.md in 5 changes) and do not affect code correctness; they are
reported, not fixed, per instructions.
