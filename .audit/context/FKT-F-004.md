# Context pack: FKT-F-004 — isoformat 'T' raw writers vs ORM space-format due queries

## Candidate statement (exact)
"SQLite stores DateTime columns as text; SQLAlchemy writes/compares space-separated ('YYYY-MM-DD HH:MM:SS'), isoformat() writes 'T'-separated. Because ' ' < 'T' in ASCII, a same-day row stored with 'T' is lexicographically AFTER the bound datetime → silently excluded from due queries until the date flips."

## Contract evidence
- repository.py:270-285 `get_trend_analysis` comment — the v1 fix that documents the trap: "SQLite stores DateTime as 'YYYY-MM-DD HH:MM:SS' while isoformat() uses 'T', so a string compare lexicographically mis-excludes ... (space < 'T')". Established in-repo invariant: bind datetime OBJECTS, never isoformat strings.
- models.py DateTime columns compared with bound datetimes in: repository.py:28-34 (`get_items_due`), :58-64 (`get_stats`), :76-80 (`get_learning_today`); concept_scheduler.py:235-249 (`get_due_concepts`).

## Source locations (minimal)
- 'T' writers (raw SQL): tools/populate.py:57 (sessions start_ts/end_ts), :76 (multi_modal_logs), :100-107 (tracked_concepts first_seen/last_seen/next_review), :121/:124 (memory_decay); tools/preflight_check.py:57 hardcoded literal `"2025-10-02T10:00:00"` (multi_modal_logs).
- ORM due queries (space format): repository.py:28-34, :58-64; concept_scheduler.py:242 (`next_review <= now`).
- Documented trap: repository.py:270-285.

## Reproduction (temp DB; live DB read-only)
1. Fresh temp DB `C:\Users\hp\AppData\Local\Temp\opencode\f004.db`; create tables via `venv\Scripts\python.exe -c "from tracker_app.db.db_module import init_db; init_db()"` with `$env:FKT_TEST_DB` set.
2. Seed tracked_concepts via raw sqlite3: row A `next_review='2026-08-13T09:00:00'` (T), row B `next_review='2026-08-13 08:00:00'` (space); both `concept` PK, first_seen/last_seen text.
3. Query via ORM: `ConceptScheduler().get_due_concepts()` with `now` fixed (monkeypatch or compute in-process) at `2026-08-13 10:00:00` — Expected: both A and B due. Observed: only B (A lexicographically > '2026-08-13 10:00:00' because 'T' > ' ').
   Equivalent repository probe: `LearningRepository.get_items_due` with learning_items seeded the same way on next_review_date.
4. Live read-only: `SELECT COUNT(*) FROM tracked_concepts WHERE next_review LIKE '%T%'` vs `LIKE '% %'` on tracker_app/data/sessions.db (finding reports 54 'T' vs 341 ' ').

## Assertion points
- Which seeded rows the ORM due query returns (ids), for both a same-day and a next-day bound cutoff.
- Live DB mix of 'T'/' ' formats in the same column.

## Traps
- Use FIXED seed dates + fixed query datetime (not `datetime.utcnow()`) so the probe is deterministic.
- populate.py seeds the real DB if pointed at it — set FKT_TEST_DB to the temp path before running any tool, or run its SQL manually against temp.
- Live DB: SELECT only.
- Do not modify repository.py; it is the correct-behavior reference (v1 fix).

## Unresolved
- Whether seeded 'T' rows are repaired by a data migration or accepted (finding: latent for prod, live for seeded DBs).
