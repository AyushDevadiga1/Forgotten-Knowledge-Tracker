# Context pack: FKT-F-001 — FKT_TEST_DB/engine rebinding contract broken

## Candidate statement (exact)
"Once tracker_app.config (or web.app) is imported, later FKT_TEST_DB=... is ignored and the engine/session binds to the REAL tracker_app/data/sessions.db. Additionally, `from tracker_app.db.models import SessionLocal` at module scope captures a proxy that forwards to the module-global `_SessionLocal`, so test patching via `models.SessionLocal = <patched>` has no effect on those consumers → writes leak into the real DB."

## Contract evidence
- models.py:18-23 (docstring): "tests can safely set FKT_TEST_DB at the top of a test file and get the correct DB path" — the documented contract being violated.
- config.py:32: `DB_PATH = os.environ.get('FKT_TEST_DB', str(DATA_DIR / "sessions.db"))` — evaluated once at import.
- models.py:33-34: `get_engine()` re-imports config expecting a fresh value — no-op due to module cache.

## Source locations (minimal)
- tracker_app/config.py:32 — env read frozen at import.
- tracker_app/db/models.py:13 (module-level `from tracker_app.config import DB_PATH`), :29-51 (`get_engine`), :54-60 (`get_session_local`), :67-76 (`_LazySessionProxy.__call__` → `get_session_local()`, ignores `models.SessionLocal` rebinding), :93-98 (`get_db`).
- Module-scope importers: tracking/activity_monitor.py:12, learning/concept_scheduler.py:9, learning/concept_promotion.py:16 (each does `from tracker_app.db.models import SessionLocal` at import).
- web/app.py:28-29 — `init_all_databases()` at import time binds engine to real DB.
- Workaround comments: tests/test_api.py:36-41, tests/test_concept_scheduler.py:27-32, tests/test_concept_promotion.py:27 (each re-binds the consumer module's SessionLocal).

## Reproduction (temp DB; read-only on repo)
Run from repo root with venv python; never connect the real engine:
1. Env-rebind probe (silent real-DB bind):
   `venv\Scripts\python.exe -c "import tracker_app.config; from tracker_app.db import models; from tracker_app.config import DB_PATH as p1; import os; os.environ['FKT_TEST_DB']=r'C:\Users\hp\AppData\Local\Temp\opencode\f001_other.db'; models._engine=None; from tracker_app.config import DB_PATH as p2; print(p1, p2, models.get_engine().url)"`
   Expected (per contract): p2/engine.url == the new temp path. Observed: p1==p2==real `...\tracker_app\data\sessions.db` (URL inspection only — do not connect).
2. Proxy-rebind probe: import `SessionLocal` from models as `proxy`; set `models.SessionLocal = sessionmaker(bind=create_engine('sqlite:///<temp>'))`; then `proxy().get_bind().engine.url` — expected temp, observed real engine (proxy forwards to `_SessionLocal`, not the module attribute).

## Assertion points
- engine URL string before/after env set + `_engine=None`.
- `proxy().get_bind().engine.url` after rebinding `models.SessionLocal`.
- Same for `cs_mod.SessionLocal` (concept_scheduler) — import-time capture.

## Traps
- Do NOT import `tracker_app.web.app` with FKT_TEST_DB unset — it calls `init_all_databases()` (create_all) on the real DB at import.
- Do not execute queries through the real engine; only print `.url`.
- config.py also `load_dotenv()`s root `.env` — check .env for FKT_TEST_DB if results confuse.

## Unresolved
- Which consumers import `models.engine` directly (db_module.py:5 `get_engine`) vs the proxy (db_module.py:5 `Base`)? Engine rebinding path for a fix.
- Does .env set FKT_TEST_DB currently?
