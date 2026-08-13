## 1. Fix raw-SQL writers

- [x] 1.1 `tracker_app/tools/populate.py`: replace `isoformat()` with space-separated storage format (`str(dt)`) in all DateTime-column inserts (sessions: start/end; multi_modal_logs: ts; tracked_concepts: first_seen/last_seen/next_review; memory_decay: last_seen_ts/updated_at)
- [x] 1.2 `tracker_app/tools/preflight_check.py`: replace hardcoded `'2025-10-02T10:00:00'` with `'2025-10-02 10:00:00'` (space form)

## 2. Normalize existing rows

- [x] 2.1 `tracker_app/db/migrations.py`: append migration `011_datetime_storage_format` — for each affected column (tracked_concepts.next_review/first_seen/last_seen, sessions.start_ts/end_ts, multi_modal_logs.timestamp, memory_decay.last_seen_ts/updated_at): `UPDATE <t> SET <col> = substr(<col>,1,10) || ' ' || substr(<col>,12) WHERE <col> LIKE '____-__-__T%'`
- [x] 2.2 Verify `python -m tracker_app.db.migrations` with a FKT_TEST_DB containing seeded 'T' rows normalizes them (applied=11)

## 3. Regression coverage

- [x] 3.1 Test: seed tracked_concepts with a 'T'-format next_review row → run migrations → row stored space-format → `get_due_concepts` includes it at the correct boundary
- [x] 3.2 Test: migration 011 is a no-op when no 'T' rows exist (idempotent)
- [x] 3.3 Run `venv\Scripts\python.exe -m pytest tracker_app/tests -q` and confirm full suite green

## 4. Coordination

- [x] 4.1 This change and drop-duplicate-feedback-index both append to MIGRATIONS in migrations.py — apply this change (011) BEFORE drop-duplicate-feedback-index (012) and re-run both tasks' regression tests
  - Done: 011 is the last migration in the registry; drop-duplicate-feedback-index (012) is not yet in the tree, so the ordering constraint holds by construction. When 012 lands, re-run both changes' regression suites.
