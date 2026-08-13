# Context pack: FKT-F-002 — run_migrations() never wired into startup

## Candidate statement (exact)
"An existing DB that predates any migration-only column fails at runtime on first ORM write (e.g. api.py:426-434 updates prompted_at; concept_scheduler.py:189-204 writes repetitions/review_count) because no startup path applies migrations."

## Contract evidence
- migrations.py:1 ("Applies idempotent MIGRATIONS in order"), :13-29 `ensure_base_schema` docstring ("makes `python -m tracker_app.db.migrations` self-sufficient"), :32-34 ("SQL must be idempotent") — design intent is automatic, safe schema convergence; it is only wired to `__main__` (migrations.py:271) and tools/launcher.py `migrate`.
- Migration-only columns (models reference but only migrations create on legacy DBs): prompted_at (007, models.py:184), window_title (008, models.py:185), repetitions (009, models.py:240), review_count/correct_count (010, models.py:241-242), attention_at_encoding/lambda_personalised (002, models.py:245-246).
- db_module.py:15-23: `init_db()` = `Base.metadata.create_all` only — never ALTERs existing tables.

## Source locations (minimal)
- tracker_app/db/migrations.py:160-230 (`run_migrations`), :262-280 (`__main__`).
- tracker_app/web/app.py:28-29 — `init_all_databases()` at import (create_all only).
- tracker_app/tracking/loop.py:274 — `init_all_databases()` in `track_loop`.
- tracker_app/db/db_module.py:15-23 — init = create_all only.
- First ORM writers of migration-only columns: web/api.py:426-434 (prompted_at UPDATE), learning/concept_scheduler.py:189-222 (repetitions/review_count).
- CI evidence: .github/workflows/ci.yml runs `python -m tracker_app.db.migrations` explicitly — the only automated application is a manual/CI step.

## Reproduction (temp DB; never touch real data/sessions.db)
1. Old-schema crash probe:
   ```
   $env:FKT_TEST_DB='C:\Users\hp\AppData\Local\Temp\opencode\f002_old.db'
   venv\Scripts\python.exe -c "
   import sqlite3, os
   db=r'C:\Users\hp\AppData\Local\Temp\opencode\f002_old.db'
   if os.path.exists(db): os.remove(db)
   c=sqlite3.connect(db); c.execute('CREATE TABLE intent_predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, predicted_intent TEXT, confidence REAL, context_keywords TEXT, user_feedback INTEGER, actual_intent TEXT, feedback_timestamp TEXT)'); c.commit(); c.close()
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker
   from datetime import datetime
   from tracker_app.db.models import IntentPrediction
   s=sessionmaker(bind=create_engine('sqlite:///'+db))()
   s.add(IntentPrediction(timestamp=datetime.utcnow(), predicted_intent='idle', confidence=0.5, context_keywords='[]'))
   s.commit()"
   ```
   Expected (contract): schema converges or clear migration step. Observed: `OperationalError: table intent_predictions has no column named prompted_at`.
2. Startup-does-not-migrate probe: fresh temp DB, `import tracker_app.web.app` (safe — init_all_databases writes only to the temp DB), then `SELECT name FROM sqlite_master WHERE type='table'` → schema_migrations ABSENT proves no migration path runs at startup.

## Assertion points
- Exception class + message of the ORM commit in probe 1.
- schema_migrations table absence after `import tracker_app.web.app` on fresh temp DB.
- Contrast: run `venv\Scripts\python.exe -m tracker_app.db.migrations` with FKT_TEST_DB=temp → 010 applied, schema_migrations populated, same ORM write succeeds.

## Traps
- `python -m tracker_app.db.migrations` with FKT_TEST_DB unset migrates the REAL DB — always set FKT_TEST_DB in probes.
- Live data/sessions.db is fully migrated (schema_migrations 001-010); live DB inspection must be read-only.

## Unresolved
- Whether auto-migration at startup is desired (behavior change) vs documenting a mandatory migration step — affects fix direction.
