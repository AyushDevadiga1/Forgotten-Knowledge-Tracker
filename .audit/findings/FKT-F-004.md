# FKT-F-004 � Raw-SQL writers store isoformat() "T" datetimes; ORM due-queries compare space format ? same-day due misclassification (sibling of v1 trend-boundary bug)

- ID: FKT-F-004
- STATUS: VERIFIED
- SEVERITY: MEDIUM
- SCOPE: tracker_app.db.models DateTime columns ? raw-SQL writers (tracker_app/tools/populate.py, preflight_check.py) ? due queries (repository.get_items_due, concept_scheduler.get_due_concepts)
- LOCATION:
  - Writers storing `...isoformat()` ('T' separator): tracker_app/tools/populate.py:57 (sessions), :76 (multi_modal_logs), :100-107 (tracked_concepts first_seen/last_seen/next_review), :121/:124 (memory_decay); tracker_app/tools/preflight_check.py:52 (multi_modal_logs)
  - ORM consumers binding datetime objects (space format): tracker_app/db/repository.py:28-34 (get_items_due), :61-64 (get_stats); tracker_app/learning/concept_scheduler.py:240-249 (get_due_concepts)
  - Documented trap: tracker_app/db/repository.py:270-285 comment (v1 fix: "isoformat() uses 'T' � space < 'T'")
- CLAIM: SQLite stores DateTime columns as text; SQLAlchemy writes/compares space-separated ('YYYY-MM-DD HH:MM:SS'), isoformat() writes 'T'-separated. Because ' ' < 'T' in ASCII, a same-day row stored with 'T' is lexicographically AFTER the bound datetime ? silently excluded from due queries until the date flips. Live DB already has mixed formats in tracked_concepts.next_review (54 'T' rows vs 341 ' ' rows from populate.py seeding).
- EXPECTED: All writers of DateTime columns must use the same textual format as the ORM (space), so due-ordering is consistent.
- OBSERVED: Probe: row stored '2026-08-13T09:00:00' excluded from `next_review <= 2026-08-13 10:00:00` while '2026-08-13 08:00:00' included. Live DB row mix confirms real-world exposure. No current production writer uses isoformat (populate.py is a dev/seed tool) � latent for prod, live for seeded DBs.
- EVIDENCE: logic-hunter H4 (probe), contract-hunter H2 (live DB counts), runtime-hunter H5.
- REPRODUCTION: CONFIRMED (bug-reproducer, 2026-08-13 � deterministic probe; evidence appended below)
- ROOT_CAUSE: (tentative) no storage-format invariant enforced for DateTime columns; raw-SQL writers bypass ORM type formatting.
- RELATED_PATTERN: P-004
- AFFECTED_INSTANCES: (pending)
- FIX: (implemented, OpenSpec change "normalize-datetime-storage-format")
  - tracker_app/tools/populate.py: replaced `datetime.isoformat()` with `str(dt)` (ORM/SQLite storage format
    'YYYY-MM-DD HH:MM:SS[.ffffff]') in every DateTime-column insert — sessions start_ts/end_ts, multi_modal_logs
    timestamp, tracked_concepts first_seen/last_seen/next_review, memory_decay last_seen_ts/updated_at.
  - tracker_app/tools/preflight_check.py: hardcoded `'2025-10-02T10:00:00'` → `'2025-10-02 10:00:00'` (space form).
  - tracker_app/db/migrations.py: appended migration `011_datetime_storage_format` (after 010): 8 LIKE-guarded
    UPDATEs (`WHERE <col> LIKE '____-__-__T%'`, `substr(col,1,10) || ' ' || substr(col,12)`) normalizing legacy
    'T' rows for tracked_concepts (next_review, first_seen, last_seen), sessions (start_ts, end_ts),
    multi_modal_logs (timestamp), memory_decay (last_seen_ts, updated_at). Idempotent — no-op when no 'T' rows.
- OPENSPEC_CHANGE: normalize-datetime-storage-format
- REGRESSION_TEST: tracker_app/tests/test_datetime_storage_format.py (3 tests, all pass; verified to FAIL without
  the fix via negative control with 011 stripped): (1) raw-seeded 'T'-format next_review row excluded from
  ConceptScheduler.get_due_concepts at the same-day boundary → run_migrations → stored space-format and included
  at that boundary while a genuinely future row stays excluded; (2) migration 011 no-op when no 'T' rows exist
  (first run applied=11, second run skipped=11, rows byte-for-byte unchanged); (3) populate.py emits space-format
  values into all 8 affected DateTime columns (executed via subprocess against a throwaway FKT_TEST_DB).
  test_migrations_at_startup.py TOTAL_MIGRATIONS 10→11 (forced by appending a migration).
- VERIFICATION: `venv\Scripts\python.exe -m pytest tracker_app/tests/test_datetime_storage_format.py -q` → 3 passed;
  `python -m tracker_app.db.migrations` with a FKT_TEST_DB seeded with 'T' rows → "11 applied, 0 skipped, 0 failed"
  and all 8 columns normalized (incl. microsecond form); full suite
  `venv\Scripts\python.exe -m pytest tracker_app/tests -q` → 252 passed (stable across 2 consecutive runs).
  Live-DB guard: size unchanged (765952 bytes); mtime 2026-08-12T07:10:15 → 2026-08-13T18:36:30 — touched by a
  PARALLEL process (FKT-F-005 work) 10 s before this change's test file existed; my test runs verified to never
  touch data/sessions.db (mtime stable across re-runs). Read-only inspection of the live DB shows the content
  change is exactly the intended 011 normalization (T-rows 54/100/200/54 → 0, schema_migrations=11, concept
  total 395 unchanged).
- REMAINING_RISK: resolved for existing seeded DBs (migration 011 repairs them at next startup run). A future raw
  writer that reintroduces isoformat() 'T' values would re-trigger the bug — the invariant is now documented in
  repository.py:270-285, the writer code, and this change's proposal.



## REPRODUCTION (bug-reproducer evidence gate, 2026-08-13)

Classification: CONFIRMED � deterministic, reproduced on a throwaway DB with fixed dates; live-DB mix corroborated read-only.

### Expected behavior (from evidence)
Due queries bind datetime OBJECTS. SQLAlchemy 2.0.51 sqlite DATETIME bind format is space-separated
`%(year)04d-%(month)02d-%(day)02d %(hour)02d:%(minute)02d:%(second)02d.%(microsecond)06d`; result parsing
uses `datetime.fromisoformat()` (accepts both separators). A row with next_review = 2026-08-13 09:00:00 is
semantically due at bound 2026-08-13 10:00:00 regardless of the textual separator used at write time.
In-repo invariant documented at tracker_app/db/repository.py:270-285: "Bind the datetime OBJECT, not a
string: SQLite stores DateTime as 'YYYY-MM-DD HH:MM:SS' while isoformat() uses 'T', so a string compare
lexicographically mis-excludes ... (space < 'T')".

### Setup (deterministic)
- Fresh throwaway DB `%TEMP%\opencode\f004_repro.db`; `FKT_TEST_DB` set BEFORE any tracker_app import;
  tables via `init_db()`.
- Raw-seeded via sqlite3 (populate.py style), no utcnow anywhere:
  - rowA_space / itemA_space: next_review = '2026-08-13 08:00:00.000000' (ORM/space format)
  - rowB_T     / itemB_T:     next_review = '2026-08-13T09:00:00'         (isoformat 'T' format)
- Clock: module-level `datetime.utcnow` in concept_scheduler & repository replaced with a class returning
  the FIXED bound datetime(2026, 8, 13, 10, 0, 0) (and 2026-08-14 for the date-flip control).
- Commands: `venv\Scripts\python.exe %TEMP%\opencode\repro_f004.py`; live DB:
  `venv\Scripts\python.exe %TEMP%\opencode\live_f004.py`.

### Observed behavior (verbatim outputs)

Stage 1 � ConceptScheduler.get_due_concepts(limit=50), bound 2026-08-13 10:00:00:
  returned ids: ['rowA_space']
  rowA_space returned: True  (expected True)
  rowB_T     returned: False (expected True -> BUG: row due 09:00 excluded)

Stage 2 � LearningRepository.get_items_due(limit=50), same bound:
  returned ids: ['itemA_space']
  itemA_space returned: True  (expected True)
  itemB_T     returned: False (expected True -> BUG: same defect on learning_items path)

Stage 3 � raw SQLite lexicographic mechanism (exact SQLAlchemy bound string):
  ord(' ')=32  ord('T')=84  (space < T)
  SELECT '2026-08-13T09:00:00'        <= '2026-08-13 10:00:00.000000' -> 0
  SELECT '2026-08-13 08:00:00.000000' <= '2026-08-13 10:00:00.000000' -> 1
  SELECT concept FROM tracked_concepts WHERE next_review <= '2026-08-13 10:00:00.000000' -> ['rowA_space']

Stage 4 � date-flip control, bound 2026-08-14 10:00:00 (no reseeding):
  rowB_T now returned: True  (T-row appears exactly one day late � "excluded until the date flips")

Stage 5 � ORM write of datetime(2026,8,13,11,0,0) stored as: 2026-08-13 11:00:00.000000 (space)

Stage 6 � parser check: fromisoformat('2026-08-13T09:00:00') -> 2026-08-13 09:00:00 (T-rows parse fine
  when included; the defect is purely the SQL-level string comparison, no crash path)

Stage 7 � controls at bound 2026-08-13 10:00:00: returned ['rowA_space', 'rowD_prevday_T']
  rowD_prevday_T     (due 08-12, T-format) returned: True  (overdue T-row IS due � only same-day T rows misclassified)
  rowC_nextday_space (due 08-14)            returned: False (correctly not due)
  rowB_T             (due 08-13 09:00, T)   returned: False (BUG)

### Live DB corroboration (read-only, sqlite URI mode=ro, journal_mode=wal)
  tracked_concepts.next_review:     total=395  T-format=54  space-format=341   (matches finding's 54/341)
  learning_items.next_review_date:  total=59   T-format=0   space-format=59    (latent on this path today)
  sessions.start_ts:                total=100  T-format=100 space-format=0
  multi_modal_logs.timestamp:       total=200  T-format=200 space-format=0
  memory_decay.last_seen_ts:        total=54   T-format=54  space-format=0
  (100% T in sessions/logs/memory_decay is consistent with populate.py being their raw writer.)

### Writer code evidence (raw SQL isoformat() into DateTime columns)
- tracker_app/tools/populate.py:57 sessions start_ts/end_ts = start.isoformat(), end.isoformat()
- tracker_app/tools/populate.py:76 multi_modal_logs timestamp = ts.isoformat()
- tracker_app/tools/populate.py:100-101 tracked_concepts first_seen/last_seen = .isoformat()
- tracker_app/tools/populate.py:107 tracked_concepts next_review = next_review.isoformat()
- tracker_app/tools/populate.py:121/124 memory_decay last_seen_ts/updated_at = .isoformat()
- tracker_app/tools/preflight_check.py:57 hardcoded literal "2025-10-02T10:00:00" into multi_modal_logs.timestamp
- No other isoformat() call in the repo targets a SQLite DateTime column (remaining uses are JSON/display:
  web/api.py:439,513,714; tracking/session_state.py:58,71; tracking/activity_monitor.py:266; db/migrations.py:143;
  db/repository.py:107 display dict). Supports "latent for prod writers, live for seeded/legacy DBs".

### Notes for FIX planning
- LearningRepository.get_items_due and get_stats share the same `next_review_date <= datetime.utcnow()`
  pattern (repository.py:28-34, :61-64); ConceptScheduler.get_due_concepts (concept_scheduler.py:242) is the
  tracked_concepts due path actually hit by seeded 'T' rows today.
- A writer-side fix does not repair the 54 already-seeded 'T' rows (data repair = migration or out of scope).
