## Why

Confirmed audit finding FKT-F-001: `tracker_app.config.DB_PATH` is computed once at import time (config.py:32), so setting `FKT_TEST_DB` after `tracker_app.config` (or any module importing it) has already been imported silently has no effect — the engine binds to the real `tracker_app/data/sessions.db`. Additionally, `from tracker_app.db.models import SessionLocal` at module scope captures a proxy that always forwards to the module-global `_SessionLocal`, so test patching via `models.SessionLocal = <patched>` is silently bypassed for module-scope importers (activity_monitor, concept_scheduler, concept_promotion). The result is silent writes to the production database from tests/DB-switch code. The module's own comment (models.py:18-23) promises "tests can safely set FKT_TEST_DB at the top of a test file and get the correct DB path" — that contract is currently false.

## What Changes

- `tracker_app/config.py`: add `get_db_path()` that reads `FKT_TEST_DB` from the environment at call time (fallback `DATA_DIR / "sessions.db"`); keep the module constant `DB_PATH` for backward compatibility.
- `tracker_app/db/models.py`:
  - `get_engine()` resolves the DB path via `get_db_path()` instead of the frozen import-time `DB_PATH`.
  - `_LazySessionProxy.__call__` re-resolves the current module attribute: if `models.SessionLocal` has been rebound to a different object, delegate to that object (so import-time captures honor rebinding); otherwise forward to the lazily created `_SessionLocal` as today.
  - `_LazyEngineProxy.__getattr__` likewise re-resolves a rebound `models.engine` before forwarding.
- No change to `web/app.py` (import-time `init_all_databases()` remains; documented as remaining risk — the engine may already exist when a later env switch happens).

## Capabilities

### New Capabilities
None.

### Modified Capabilities
`db.engine-lifecycle`: FKT_TEST_DB honored when set any time before first engine creation; `models.SessionLocal`/`models.engine` rebinding honored by module-scope importers.

## Impact

- Modified: `tracker_app/config.py`, `tracker_app/db/models.py`
- No schema change; no behavior change for normal app startup (env not set → same default path).
- Test-file workarounds that re-bind consumer-module `SessionLocal` become redundant but remain harmless.

## Notes

- Known limitation (documented in finding as remaining risk): if the engine was already created (e.g. `web/app.py` import runs `init_all_databases()`), a later env switch cannot rebind it. Full fix for that requires deferring import-time DB init and is out of scope here.
