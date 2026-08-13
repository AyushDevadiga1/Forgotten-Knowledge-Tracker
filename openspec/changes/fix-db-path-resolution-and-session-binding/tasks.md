## 1. Resolve DB path at call time

- [x] 1.1 `tracker_app/config.py`: add `get_db_path()` returning `os.environ.get('FKT_TEST_DB', str(DATA_DIR / "sessions.db"))`; keep `DB_PATH` constant (now defined as `get_db_path()` at import for backward compatibility)
- [x] 1.2 `tracker_app/db/models.py` `get_engine()`: use `config.get_db_path()` (re-read at call time) instead of the frozen `DB_PATH` import

## 2. Make lazy proxies honor rebinding

- [x] 2.1 `_LazySessionProxy.__call__`: re-resolve the current module attribute — if `models.SessionLocal` is no longer this proxy, delegate to the rebound object; else forward to `get_session_local()` as today
- [x] 2.2 `_LazyEngineProxy.__getattr__`: re-resolve the current module attribute — if `models.engine` is rebound, delegate; else forward to `get_engine()`

## 3. Regression coverage

- [x] 3.1 Test: `config.get_db_path()` reflects a later `FKT_TEST_DB` change
- [x] 3.2 Test: rebinding `models.SessionLocal` is honored by a module-scope importer (e.g. `concept_scheduler.SessionLocal` returns sessions bound to the rebound engine)
- [x] 3.3 Test: rebinding `models.engine` is honored by `models.engine` attribute access
- [x] 3.4 Run `venv\Scripts\python.exe -m pytest tracker_app/tests -q` and confirm full suite green
