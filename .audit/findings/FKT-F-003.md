# FKT-F-003 � learning_items.last_review_date exists in schema but is unmapped by model: permanent null, SM-2 retention state never persisted

- ID: FKT-F-003
- STATUS: VERIFIED
- SEVERITY: MEDIUM
- SCOPE: tracker_app.db.models.LearningItem ? migrations 005 ? learning_tracker/sm2_memory_model
- LOCATION:
  - tracker_app/db/migrations.py:82-85 � `005_learning_item_last_review` ALTER TABLE learning_items ADD COLUMN last_review_date TEXT
  - tracker_app/db/models.py:122-149 � LearningItem declares next_review_date (line 136) but NO last_review_date attribute
  - tracker_app/learning/learning_tracker.py:270 � `'last_review_date': getattr(row, 'last_review_date', None)` (always None)
  - tracker_app/learning/learning_tracker.py:300-301 � `_dict_to_sm2item` reads item_dict.get('last_review_date') (always None)
  - tracker_app/learning/sm2_memory_model.py:130 � `item.last_review_date = datetime.utcnow()` (in-memory only; never persisted); :170 estimate_retention uses it
- CLAIM: Schema-model drift: the column exists in migrated DBs but the ORM model neither maps nor writes it. API row serialization always returns last_review_date: null even after reviews; SM-2 retention estimate loses last-review time across restarts. Writing it via the ORM is impossible (attribute missing ? AttributeError).
- EXPECTED: Either the model maps the column and persists it on review, or the column/migration is removed; the API surface must not promise a field that can never be non-null.
- OBSERVED: Live DB schema has last_review_date TEXT; `SELECT COUNT(*) FROM learning_items WHERE last_review_date IS NOT NULL` ? 0. Runtime probe: schema-missing-from-model=['last_review_date'], model-missing-from-schema=[] for learning_items. No writer for last_review_date anywhere in repo (grep).
- EVIDENCE: contract-hunter H1, runtime-hunter H3, logic-hunter H5; live DB inspection.
- REPRODUCTION: CONFIRMED � see REPRODUCTION/STATUS below (bug-reproducer, 2026-08-13)
- ROOT_CAUSE: (tentative) migration added a column the model never adopted (unfinished feature); consumers papered over with defensive getattr.
- RELATED_PATTERN: P-003
- AFFECTED_INSTANCES: (pending)
- FIX: `LearningItem` now maps the column — `last_review_date = Column(DateTime, nullable=True)` after `next_review_date` (tracker_app/db/models.py). `record_review` persists `item_record.last_review_date = review_date` on both the sm2 and leitner paths before `LearningRepository.record_review` (tracker_app/learning/learning_tracker.py). `_row_to_dict` serializes the real value via direct `row.last_review_date` access (previously `getattr(..., None)`). No DDL change: column already exists via migration 005 on migrated DBs; `create_all` creates it on fresh DBs. SM-2 retention state now survives a DB round-trip (`_dict_to_sm2item` reloads a real timestamp).
- OPENSPEC_CHANGE: map-learning-item-last-review-date
- REGRESSION_TEST: tracker_app/tests/test_learning_tracker.py — `test_review_sm2_persists_last_review_date` and `test_review_leitner_persists_last_review_date` assert `get_item()['last_review_date']` is non-null after `record_review(quality_rating=5, algorithm='sm2'|'leitner')` and that a fresh-session reload of the DB row still sees it. Verified both FAIL on pre-fix code (2 failed) and PASS after the fix. No pre-existing test asserted the buggy None behavior or relied on the getattr fallback, so no existing test was changed.
- VERIFICATION: `venv\Scripts\python.exe -m pytest tracker_app/tests/test_learning_tracker.py -q` → 10 passed. Full suite `venv\Scripts\python.exe -m pytest tracker_app/tests -q` → 242 passed (240 pre-existing + 2 new), 0 failed (2026-08-13).
- REMAINING_RISK: fix direction (map+persist vs drop column) must be evidence-driven; check API consumers of last_review_date before choosing.

## REPRODUCTION/STATUS � bug-reproducer (2026-08-13)

CLASSIFICATION: CONFIRMED

Core claim proven with runtime evidence. One mechanism detail corrected (see "ORM write" below): no AttributeError � the write silently succeeds and the value is silently dropped at commit.

### Environment
- Windows 10/11, Python 3.13.7 (venv\Scripts\python.exe)
- All probes in fresh subprocesses with `FKT_TEST_DB` set before import; repo root on PYTHONPATH
- Temp DBs: C:\Users\hp\AppData\Local\Temp\opencode\f003_m.db (migrated), f003_api.db (create_all)
- Live DB (read-only SELECT/PRAGMA only): tracker_app\data\sessions.db

### Command 1 � fresh temp DB via migration runner
    $env:FKT_TEST_DB='C:\Users\hp\AppData\Local\Temp\opencode\f003_m.db'
    venv\Scripts\python.exe -m tracker_app.db.migrations
Output: "005_learning_item_last_review ... [OK]" � "Done: 10 applied, 0 skipped, 0 failed"

### Command 2 � schema vs ORM model (subprocess, FKT_TEST_DB=f003_m.db)
    PRAGMA table_info(learning_items) -> SCHEMA has last_review_date: True
    hasattr(LearningItem, 'last_review_date') -> False
    hasattr(LearningItem, 'next_review_date') -> True
    LearningItem.__table__.columns -> ['answer', 'correct_count', 'created_at', 'difficulty',
      'ease_factor', 'id', 'interval', 'item_type', 'next_review_date', 'question',
      'repetitions', 'status', 'success_rate', 'tags', 'total_reviews', 'updated_at']
    (no last_review_date)
EXPECTED: model maps every schema column. OBSERVED: column exists in DB, absent from model (drift).

### Command 3 � ORM write attempt (both flush orderings; subprocess)
    item = LearningItem(...); item.last_review_date = datetime.utcnow(); db.commit()
Output: SET item.last_review_date: no exception � COMMIT: ok
    DB row after commit: SELECT last_review_date ... -> (None,)
    Same result when attribute set BEFORE flush: commit ok, DB -> (None,)
    Raw-SQL write (UPDATE ... SET last_review_date='...') then ORM reload:
      getattr(reloaded, 'last_review_date', 'MISSING') -> MISSING (ORM cannot read it either)
EXPECTED (candidate): AttributeError on write. OBSERVED: NO AttributeError � assignment is
silently accepted as a plain Python attribute (in instance __dict__) but SQLAlchemy does not
persist it and cannot read it back. MECHANISM CORRECTION: defect is silent value loss, not a
loud AttributeError. Functional claim (ORM neither maps nor writes the column) holds.

### Command 4 � API serialization on a MIGRATED DB (column present; subprocess)
    tracker = LearningTracker()
    item_id = tracker.add_learning_item(...)
    tracker.get_item(item_id)['last_review_date']            -> None
    tracker.record_review(item_id, quality_rating=5, algorithm='sm2')
    tracker.get_item(item_id)['last_review_date']            -> None   (unchanged)
    DB row: last_review_date -> None | next_review_date -> 2026-08-14 ... (persisted)
    Web surface: GET /api/v1/items -> get_items() -> _row_to_dict (api.py:131-146, 145)
    record_review writes interval/ease/repetitions/next_review_date/... (learning_tracker.py:137-146)
    but never last_review_date.
EXPECTED: last_review_date becomes non-null after a review. OBSERVED: always None in API
output AND in the DB row, even though the column exists (migrated DB).

### Command 5 � SM-2 in-memory state vs reload (subprocess)
    item = SM2Item(...)
    BEFORE review:  last_review_date None; estimate_retention -> all 0.0
    calculate_next_interval(item, 5):
    AFTER review:   last_review_date 2026-08-13 01:22:53.278659 (in memory, set at
                    sm2_memory_model.py:130); estimate_retention -> now 1.0, 1_day 0.403, ...
    Reload path: _dict_to_sm2item({'last_review_date': None, ...})  # what _row_to_dict yields
    RELOADED:       last_review_date None; estimate_retention -> all 0.0
EXPECTED: last-review time survives a DB round-trip. OBSERVED: in-memory value is lost on
reload; retention estimate collapses to zeros (estimate_retention returns zeros when
last_review_date is None, sm2_memory_model.py:170-177).

### Command 6 � live DB corroboration (READ-ONLY)
    PRAGMA table_info(learning_items) on tracker_app\data\sessions.db:
      columns end with ... 'updated_at', 'last_review_date'  -> column EXISTS
    SELECT COUNT(*) FROM learning_items                          -> 59
    SELECT COUNT(*) FROM learning_items WHERE last_review_date IS NOT NULL -> 0
EXPECTED: at least some rows carry a last-review timestamp after years of reviews.
OBSERVED: column exists (migration 005 applied at some point), zero non-null values.

### Verdict
- CONFIRMED. Schema-model drift real: column in migrated DBs, absent from LearningItem.
- Serialization always null: _row_to_dict getattr(..., None) (learning_tracker.py:270).
- Persistence broken: record_review never writes it; ORM cannot map/persist it (silent drop).
- Retention state lost across reload: _dict_to_sm2item always feeds None.
- Live data corroboration: 0/59 non-null.
- Correction to candidate: "AttributeError on ORM write" is false as stated � SQLAlchemy 2.0
  accepts the attribute assignment silently and drops it at commit. Impact is unchanged
  (silent loss), arguably worse (no error to surface the drift).
