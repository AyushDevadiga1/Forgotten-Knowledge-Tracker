# FKT-F-001 — FKT_TEST_DB/engine rebinding contract broken: silent writes to real data/sessions.db

- ID: FKT-F-001
- STATUS: VERIFIED
- SEVERITY: HIGH
- SCOPE: tracker_app.db.models (+ tracker_app.config, consumers importing SessionLocal at module scope)
- LOCATION:
  - tracker_app/config.py:32 — `DB_PATH = os.environ.get('FKT_TEST_DB', ...)` frozen at import time
  - tracker_app/db/models.py:29-51 — `get_engine()` lazy re-read of DB_PATH is a no-op (config module already cached)
  - tracker_app/db/models.py:67-76 — `_LazySessionProxy.__call__` forwards to module-global `_SessionLocal`, ignoring rebinding of `models.SessionLocal`
  - Module-scope importers of SessionLocal: tracker_app/tracking/activity_monitor.py:12, tracker_app/learning/concept_scheduler.py:9, tracker_app/learning/concept_promotion.py:16
  - tracker_app/web/app.py:28-29 — `init_all_databases()` at import time binds engine to real DB before any test body runs
- CLAIM: The documented contract (models.py:18-23: "tests can safely set FKT_TEST_DB at the top of a test file and get the correct DB path") is false in-process. Once tracker_app.config (or web.app) is imported, later `FKT_TEST_DB=...` is ignored and the engine/session binds to the REAL tracker_app/data/sessions.db. Additionally, `from tracker_app.db.models import SessionLocal` at module scope captures the proxy which forwards to the global `_SessionLocal`, so test patching via `models.SessionLocal = <patched>` has no effect on those consumers → writes leak into the real DB.
- EXPECTED: Setting FKT_TEST_DB before first engine use selects the test DB; rebinding SessionLocal must not silently write to a different database than the one bound at import.
- OBSERVED: Runtime probe (venv py3.13): env set AFTER `import tracker_app.config` → `get_engine().url` still `sqlite:///C:\...\tracker_app\data\sessions.db` even after `_engine = None` + re-call. Proxy probe: after `models.SessionLocal = sm` (in-memory), the originally-imported proxy still returned sessions bound to real get_engine(). Test files document the leak: tracker_app/tests/test_api.py:36-41 ("writes leak into the real data/sessions.db"), test_concept_scheduler.py:27-32, test_concept_promotion.py:27 — each manually re-binds the consumer module's SessionLocal as a workaround.
- EVIDENCE: hunter probes (runtime-hunter H1, logic-hunter H1) + test-file comments; recon records real data/sessions.db exists and is actively migrated.
- REPRODUCTION: CONFIRMED (bug-reproducer, 2026-08-13; venv python, fresh subprocesses, repo read-only; probe scripts under C:\Users\hp\AppData\Local\Temp\opencode\)
  Claim 1 - env rebind after import is a no-op (probe f001_probe1a.py):
    probe: import tracker_app.config; p1 = config.DB_PATH; os.environ["FKT_TEST_DB"]=<temp f001_other.db>; models._engine = None; from tracker_app.config import DB_PATH as p2; print(models.get_engine().url)
    CONFIG_DB_PATH_BEFORE     = C:\Users\hp\Desktop\FKT\tracker_app\data\sessions.db
    CONFIG_DB_PATH_AFTER_ENV  = C:\Users\hp\Desktop\FKT\tracker_app\data\sessions.db
    ENGINE_URL                = sqlite:///C:\Users\hp\Desktop\FKT\tracker_app\data\sessions.db
    ENGINE_PICKED_UP_ENV_VALUE= False
    positive control (f001_probe1b.py, env set BEFORE import): ENGINE_URL = sqlite:///C:\Users\hp\AppData\Local\Temp\opencode\f001_ctrl.db -> mechanism is purely import-ordering dependent; config module cache freezes DB_PATH.
  Claim 2 - SessionLocal rebind bypassed by import-time capture (probe f001_probe2.py; FKT_TEST_DB=<f001_probe_a.db> set pre-import; rebind models.SessionLocal = sessionmaker(bind=<f001_probe_b.db>)):
    CAPTURED_PROXY_IS_MODULE_ATTR (cs_mod.SessionLocal is models.SessionLocal, before rebind) = True
    REBOUND_ATTR_SESSION_URL   = sqlite:///C:\Users\hp\AppData\Local\Temp\opencode\f001_probe_b.db  (module-attribute consumers see the rebind)
    CAPTURED_PROXY_SESSION_URL = sqlite:///C:\Users\hp\AppData\Local\Temp\opencode\f001_probe_a.db  (cs_mod.SessionLocal still forwards to global _SessionLocal -> engine bound at first use)
    write via cs_mod.SessionLocal (TrackedConcept concept=f001-probe) + commit -> ROW_IN_TEMP_A = True, ROW_IN_TEMP_B = False
  Guard: real data/sessions.db untouched across all probes (size 765952 / mtime 2026-08-12T07:10:15+05:30 identical before and after).
  Corroboration (source, not executed): test_api.py:36-41, test_concept_scheduler.py:27-32, test_concept_promotion.py:27 re-bind the consumer module's SessionLocal and document the import-time capture.
  Not executed: pytest; importing tracker_app.web.app (init_all_databases() at app.py:28-29 binds the real DB at import - intentionally not triggered).
  CLASSIFICATION: CONFIRMED - both sub-claims reproduced with concrete outputs; real DB never opened.
- ROOT_CAUSE: CONFIRMED — config.DB_PATH snapshotted at import time (config module cache
  freezes it, so get_engine()'s lazy re-import was a no-op) + lazy proxies that forward to
  module globals without re-resolving the module attribute (import-time captures of
  SessionLocal/engine bypass later rebinding). Fix validated the root cause: call-time env
  read + identity-based re-resolution make both failure modes disappear.
- RELATED_PATTERN: P-001
- AFFECTED_INSTANCES: (pending)
- FIX: IMPLEMENTED (2026-08-13, change fix-db-path-resolution-and-session-binding)
  1. tracker_app/config.py: added `get_db_path()` which reads `os.environ['FKT_TEST_DB']`
     at call time with fallback `str(DATA_DIR / "sessions.db")`; `DB_PATH = get_db_path()`
     kept at import for backward compatibility (still frozen, as documented).
  2. tracker_app/db/models.py `get_engine()`: now calls `get_db_path()` at engine-creation
     time instead of the frozen import-time `DB_PATH`; the misleading "re-read here"
     comment was removed.
  3. tracker_app/db/models.py `_LazySessionProxy.__call__`: re-resolves the current module
     attribute (`import tracker_app.db.models as models_mod; getattr(models_mod,
     "SessionLocal", self)`); if `models.SessionLocal` is no longer this proxy instance
     it delegates to the rebound object, else forwards to `get_session_local()` (identity
     check guards against recursion).
  4. tracker_app/db/models.py `_LazyEngineProxy.__getattr__`: likewise re-resolves a
     rebound `models.engine` before forwarding to `get_engine()`.
  Not changed: web/app.py (import-time `init_all_databases()` — remaining risk as
  documented in proposal Notes).
- OPENSPEC_CHANGE: fix-db-path-resolution-and-session-binding
- REGRESSION_TEST: ADDED tracker_app/tests/test_db_path_resolution.py (4 tests, all pass
  with fix; all 4 FAIL against pre-fix code — verified via `git stash` revert of the two
  source files):
  - test_get_db_path_reflects_later_env_change — config.get_db_path() honors a later
    FKT_TEST_DB change (tasks 3.1).
  - test_get_engine_reads_env_at_call_time — claim 1: env set AFTER import is honored by
    get_engine() (frozen DB_PATH no longer consulted).
  - test_session_rebind_honored_by_module_scope_importer — claim 2: module-scope importer
    (concept_scheduler.SessionLocal) honors a later models.SessionLocal rebind; row
    asserted in rebound engine's throwaway DB, absent from the env-bound throwaway DB,
    plus `session.bind is rebound_engine` identity assert (fails before any write).
  - test_engine_rebind_honored_by_captured_proxy — captured `models.engine` proxy honors a
    later models.engine rebind (tasks 3.3).
- VERIFICATION:
  - `venv\Scripts\python.exe -m pytest tracker_app/tests/test_db_path_resolution.py -v`
    → 4 passed (against fixed code).
  - Same file with fix stashed (`git stash push -- tracker_app/config.py
    tracker_app/db/models.py`) → 4 failed; session-rebind test failed at the `db.bind`
    identity assert BEFORE any write, so no pollution of the real DB.
  - `venv\Scripts\python.exe -m pytest tracker_app/tests -q` → 240 passed, 0 failed
    (236 pre-existing + 4 new); only pre-existing datetime.utcnow() DeprecationWarnings.
  - Real data/sessions.db untouched across all runs: size 765952 / mtime
    2026-08-12T07:10:15+05:30 identical to the finding's guard values.
- REMAINING_RISK: engine created at import by web/app.py means even a correct env re-read cannot rebind an already-created engine; fix may need to cover app startup path.
