# FKT-F-006 � Duplicate index on feedback_training_samples.timestamp (migration 004 vs ORM index=True)

- ID: FKT-F-006
- STATUS: VERIFIED
- SEVERITY: LOW
- SCOPE: tracker_app.db.models.FeedbackTrainingSample ? migrations 004
- LOCATION:
  - tracker_app/db/migrations.py:79 � `CREATE INDEX IF NOT EXISTS ix_feedback_samples_timestamp ON feedback_training_samples (timestamp)`
  - tracker_app/db/models.py:334 � `timestamp = Column(DateTime, ..., index=True)` ? ORM auto-index named ix_feedback_training_samples_timestamp
- CLAIM: Two indexes exist on the same column: one created by migration 004 with a legacy name, one auto-created by create_all from the model. Duplicate write amplification; schema differs depending on init path (create_all-only ? one index; migrated ? both). All other migration-004 index names match ORM names exactly � this one is the outlier.
- EXPECTED: Exactly one index on the column; migration index name should match the ORM-generated name or the explicit index should be removed.
- OBSERVED: Live DB schema dump shows BOTH ix_feedback_samples_timestamp and ix_feedback_training_samples_timestamp on feedback_training_samples.
- EVIDENCE: contract-hunter H4 (live schema dump).
- REPRODUCTION: CONFIRMED (bug-reproducer, 2026-08-13)
- ROOT_CAUSE: migration index name diverges from ORM default name; IF NOT EXISTS allows both.
- RELATED_PATTERN: P-006
- AFFECTED_INSTANCES: (pending)
- FIX: (implemented, OpenSpec change "drop-duplicate-feedback-index")
  - tracker_app/db/migrations.py: appended migration `012_drop_duplicate_feedback_index` (after 011): executes
    `DROP INDEX IF EXISTS ix_feedback_samples_timestamp`, converging every provisioning path to the single
    ORM-managed index `ix_feedback_training_samples_timestamp` (on create_all-only DBs where the legacy index
    never existed, `IF EXISTS` makes it a no-op). Migration 004 itself is left untouched — already-applied
    migration history is not rewritten.
- OPENSPEC_CHANGE: drop-duplicate-feedback-index
- REGRESSION_TEST: tracker_app/tests/test_duplicate_feedback_index.py (2 tests, all pass; verified to FAIL
  without the fix via negative control with 012 stripped — fresh run_migrations then leaves both indexes on
  the column): (1) fresh DB after run_migrations has exactly ONE index on feedback_training_samples(timestamp),
  `ix_feedback_training_samples_timestamp`, and `ix_feedback_samples_timestamp` is absent (applied=12,
  failed=0); (2) a DB seeded with both indexes (create_all + manual legacy index) converges to the single
  index after run_migrations — first run applied=12, second run skipped=12 (idempotent), index list stays
  [ix_feedback_training_samples_timestamp]. Both tests use throwaway tmp_path DBs and guard
  tracker_app/data/sessions.db (size/mtime snapshot before/after, asserted unchanged).
  test_migrations_at_startup.py and test_datetime_storage_format.py TOTAL_MIGRATIONS 11→12 (forced by
  appending a migration).
- VERIFICATION: `venv\Scripts\python.exe -m pytest tracker_app/tests/test_duplicate_feedback_index.py -q` →
  2 passed; adjacent migration files (test_migrations_at_startup.py, test_datetime_storage_format.py,
  test_duplicate_feedback_index.py) → 7 passed; full suite
  `venv\Scripts\python.exe -m pytest tracker_app/tests -q` → 256 passed (baseline 254 + 2 new), stable
  across 2 consecutive runs. Live-DB guard: size 765952 bytes, mtime 2026-08-13T19:01:36 local — unchanged
  across both post-fix full-suite runs (the 19:01:36 write predates this fix's test runs and is attributed
  to a parallel process, same situation as noted in FKT-F-004; this change performed no schema mutation on
  the live DB).
- REMAINING_RISK: resolved — migration 012 repairs already-migrated DBs at their next run_migrations
  (startup). The live DB still carries both indexes until its next startup run; no further action needed
  after that converges.

## REPRODUCTION (bug-reproducer, 2026-08-13) � CONFIRMED

Environment: win32, venv at `venv\Scripts\python.exe`, FKT_TEST_DB set before every subprocess import.
Read-only on repo and live DB (live queries used `file:...?mode=ro` URI).

### Step 1 � Migrated path (Temp DB A): BOTH indexes present
```
Remove-Item f006a.db* ; $env:FKT_TEST_DB='...\opencode\f006a.db'; venv\Scripts\python.exe -m tracker_app.db.migrations
```
Output: all 10 migrations applied (001�010), 0 failed.
sqlite_master query result:
```
A_migrated -> ['ix_feedback_samples_timestamp', 'ix_feedback_training_samples_timestamp']
```
Index definitions (both single-column on `timestamp` � true duplicate):
```
CREATE INDEX ix_feedback_samples_timestamp           ON feedback_training_samples (timestamp)
CREATE INDEX ix_feedback_training_samples_timestamp  ON feedback_training_samples (timestamp)
```
Note: `run_migrations()` ? `ensure_base_schema()` runs `Base.metadata.create_all` BEFORE migration 004, so the ORM auto-index is created first and migration 004 adds the second, differently-named one (`IF NOT EXISTS` cannot dedupe across names).

### Step 2 � create_all-only path (Temp DB B): only the ORM index
```
Remove-Item f006b.db* ; $env:FKT_TEST_DB='...\opencode\f006b.db'; venv\Scripts\python.exe -c "from tracker_app.db.db_module import init_all_databases; init_all_databases()"
```
Output: (no output; exit 0)
```
B_create_all -> ['ix_feedback_training_samples_timestamp']
```
? Schema diverges by init path: 1 index vs 2 indexes on the same column.

### Step 3 � Live DB read-only corroboration
```
C:\Users\hp\Desktop\FKT\tracker_app\data\sessions.db  (opened with mode=ro)
LIVE read-only -> ['ix_feedback_samples_timestamp', 'ix_feedback_training_samples_timestamp']
```

### Step 4 � Migration-004 name comparison vs ORM auto names (8/8 checked)
Introspection of `Base.metadata` (SQLAlchemy metadata) vs the 004 registry parsed from `tracker_app/db/migrations.py`:
```
ix_concept_encounters_timestamp  name==auto: True  in ORM metadata: True
ix_learning_items_next_review_date name==auto: True  in ORM metadata: True
ix_learning_items_status         name==auto: True  in ORM metadata: True
ix_multi_modal_logs_timestamp    name==auto: True  in ORM metadata: True
ix_review_history_timestamp      name==auto: True  in ORM metadata: True
ix_tracked_concepts_last_seen    name==auto: True  in ORM metadata: True
ix_tracked_concepts_next_review  name==auto: True  in ORM metadata: True
ix_feedback_samples_timestamp    name==auto: False | in ORM metadata: False | auto would be ix_feedback_training_samples_timestamp
```
Exactly one diverge: `ix_feedback_samples_timestamp` on `feedback_training_samples.timestamp`.

### Classification: CONFIRMED
Every assertion point in the probe plan reproduced with concrete outputs:
1. Migrated DB has BOTH indexes (duplicate on the same single column) � reproduced in temp DB A.
2. create_all-only DB has only the ORM index � reproduced in temp DB B; schema diverges by init path.
3. Live DB (read-only) has both indexes.
4. All other 7 migration-004 index names match ORM auto names; `ix_feedback_samples_timestamp` is the sole outlier.
Expected behavior (exactly one index on the column) is violated in the migrated path.
