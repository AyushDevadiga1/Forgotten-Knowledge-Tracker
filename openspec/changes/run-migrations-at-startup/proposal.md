## Why

Confirmed audit finding FKT-F-002: `run_migrations()` is never invoked by any runtime startup path. `web/app.py:29` and `tracking/loop.py:274` call `init_all_databases()` which only runs `Base.metadata.create_all` — and `create_all` never ALTERs existing tables. An existing database created by an older FKT version (missing migration-only columns such as `intent_predictions.prompted_at`/`window_title`, `tracked_concepts.repetitions`/`review_count`/`correct_count`, `attention_at_encoding`/`lambda_personalised`) crashes on the first ORM write with `OperationalError: table ... has no column named ...`. Reproduced deterministically. The migration runner is explicitly idempotent by design (migrations.py:32-34), so invoking it at startup is safe.

## What Changes

- `tracker_app/db/db_module.py`: `init_all_databases()` (and only that entry, used by both startup paths) calls `run_migrations(db_path=<resolved path>)` after `init_db()`, so pending migrations are applied at startup.
- `run_migrations` already accepts a `db_path` parameter; pass the same resolved path used by the ORM engine (`config.get_db_path()` from the fix-db-path-resolution change) so both operate on one database.
- Fresh databases: `create_all` + migrations apply with `applied=10, skipped=0`; already-migrated databases: `applied=0, skipped=10` — both cheap and idempotent.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
`db.schema-convergence`: the runtime entry points (web dashboard, tracking loop) converge the database schema at startup instead of relying on a manual `python -m tracker_app.db.migrations` step.

## Impact

- Modified: `tracker_app/db/db_module.py`
- Behavior change: app startup now applies pending migrations automatically (intended convergence; migrations are additive/guard-guarded and idempotent).
- CI still runs `python -m tracker_app.db.migrations` explicitly — harmless with the startup call.

## Notes

- Fix direction evidence: the migration registry exists precisely to evolve old tables (migrations.py:14-20 "columns that must be added to old tables"); nothing bridged that gap at runtime.
