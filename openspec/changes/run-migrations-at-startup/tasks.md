## 1. Wire migrations into startup

- [x] 1.1 `tracker_app/db/db_module.py` `init_all_databases()`: after `init_db()`, call `run_migrations(db_path=<config.get_db_path()>)` (fall back to `DB_PATH` if helper unavailable) and log the returned counts
- [x] 1.2 Do NOT change `init_db()` itself (create_all-only contract preserved)

## 2. Regression coverage

- [x] 2.1 Test: on a stale-schema DB (intent_predictions without prompted_at/window_title), `init_all_databases()` converges the schema — subsequent `IntentPrediction` insert succeeds and `schema_migrations` exists
- [x] 2.2 Test: on an already-migrated DB, `init_all_databases()` is a no-op (applied=0)
- [x] 2.3 Run `venv\Scripts\python.exe -m pytest tracker_app/tests -q` and confirm full suite green
