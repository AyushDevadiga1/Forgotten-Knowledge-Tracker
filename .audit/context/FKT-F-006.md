# Context pack: FKT-F-006 — duplicate index on feedback_training_samples.timestamp

## Candidate statement (exact)
"Two indexes exist on the same column: one created by migration 004 with a legacy name, one auto-created by create_all from the model. Duplicate write amplification; schema differs depending on init path (create_all-only → one index; migrated → both). All other migration-004 index names match ORM names exactly — this one is the outlier."

## Contract evidence
- migrations.py:71-80 (004): every `CREATE INDEX IF NOT EXISTS` name matches the ORM `index=True` auto-name (ix_learning_items_next_review_date, ix_learning_items_status, ix_review_history_timestamp, ix_tracked_concepts_next_review, ix_tracked_concepts_last_seen, ix_concept_encounters_timestamp, ix_multi_modal_logs_timestamp) EXCEPT line 79: `ix_feedback_samples_timestamp`.
- models.py:334 `timestamp = Column(DateTime, ..., index=True)` → ORM auto-name `ix_feedback_training_samples_timestamp` (derived from table name).
- migrations.py:32-34 idempotency contract; live DBs that migrated keep both.

## Source locations (minimal)
- tracker_app/db/migrations.py:79 — legacy-name index.
- tracker_app/db/models.py:325-339 — FeedbackTrainingSample, :334 index=True.
- Contrast (correct names): models.py:136, :142, :159, :177, :230, :239, :259, :291, :306, :307.

## Reproduction (temp DB; live DB read-only)
1. create_all-only path: `$env:FKT_TEST_DB='C:\Users\hp\AppData\Local\Temp\opencode\f006a.db'`; `venv\Scripts\python.exe -c "from tracker_app.db.db_module import init_db; init_db()"`; then `sqlite3` on the temp file:
   `SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='feedback_training_samples'` → exactly `ix_feedback_training_samples_timestamp`.
2. Migrated path: `$env:FKT_TEST_DB='C:\Users\hp\AppData\Local\Temp\opencode\f006b.db'`; `venv\Scripts\python.exe -m tracker_app.db.migrations`; same query → BOTH `ix_feedback_samples_timestamp` AND `ix_feedback_training_samples_timestamp` on one column (duplicate).
3. Live read-only: same sqlite_master query on tracker_app/data/sessions.db — finding reports both indexes present.

## Assertion points
- Index-name sets differ between init paths (schema divergence).
- Duplicate index on the same single column in the migrated path (write amplification on every INSERT/UPDATE).

## Traps
- `python -m tracker_app.db.migrations` without FKT_TEST_DB set migrates the REAL DB — always set it.
- Live DB: SELECT only; if already migrated, the extra index persists until a future migration DROPs it (do not drop it yourself — that's a code change).

## Unresolved
- Whether 004's `ix_feedback_samples_timestamp` was legacy from an earlier table name (feedback_samples vs feedback_training_samples); git history may confirm.
