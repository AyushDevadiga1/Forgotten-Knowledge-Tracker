## Why

Confirmed audit finding FKT-F-006: migration 004 (migrations.py:79) creates `ix_feedback_samples_timestamp` on `feedback_training_samples.timestamp`, while the ORM model's `index=True` (models.py:334) auto-creates `ix_feedback_training_samples_timestamp` for the same column. Because the migration runner runs `ensure_base_schema` (create_all) before migration 004 and the index names differ, `IF NOT EXISTS` cannot dedupe them — migrated databases end up with two indexes on the same column (write amplification on every insert). Live DB confirmed to have both; the other 7 migration-004 index names match the ORM auto-names exactly.

## What Changes

- `tracker_app/db/migrations.py`: add migration `012_drop_duplicate_feedback_index` executing `DROP INDEX IF EXISTS ix_feedback_samples_timestamp`.
- Fresh databases converge to the single ORM-managed index; already-migrated databases are repaired on next `run_migrations` run.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
`db.schema-indexes`: `feedback_training_samples.timestamp` has exactly one index on every provisioning path.

## Impact

- Modified: `tracker_app/db/migrations.py` (+ migration 012)
- No schema or behavior change beyond index removal (write amplification eliminated).

## Notes

- Migration 004 itself is left untouched (already-applied migration history is not rewritten); the later drop is idempotent and safe for create_all-only databases too (index may not exist).
