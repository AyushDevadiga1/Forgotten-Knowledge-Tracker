## Why

Confirmed audit finding FKT-F-004: raw-SQL writers store datetimes with `isoformat()` ('T' separator) into SQLAlchemy `DateTime` columns (tracker_app/tools/populate.py:57,76,100-107,121,124; tracker_app/tools/preflight_check.py:52 with a hardcoded 'T' string at :57), while the ORM writes and compares space-separated text ('YYYY-MM-DD HH:MM:SS.ffffff'). Because ' ' < 'T' in ASCII, same-day rows written with 'T' are lexicographically AFTER the bound comparison value and are silently excluded from due queries (`ConceptScheduler.get_due_concepts`, `LearningRepository.get_items_due`/`get_stats`) until the date flips. Reproduced deterministically; the live DB already contains 54 'T'-format rows in `tracked_concepts.next_review`. This is a sibling of the v1 bug documented at repository.py:270-285.

## What Changes

- `tracker_app/tools/populate.py`: replace `datetime.isoformat()` with the ORM storage format (space separator, `str(dt)` / `%Y-%m-%d %H:%M:%S.%f`) in all DateTime-column inserts.
- `tracker_app/tools/preflight_check.py`: replace the hardcoded `'2025-10-02T10:00:00'` string with the space-separated form.
- `tracker_app/db/migrations.py`: add migration `011_datetime_storage_format` that normalizes already-stored 'T'-separated values to space-separated for the affected DateTime columns (`tracked_concepts.next_review/first_seen/last_seen`, `sessions.start_ts/end_ts`, `multi_modal_logs.timestamp`, `memory_decay.last_seen_ts/updated_at`) using `substr` surgery guarded by a `____-__-__T%` LIKE pattern (idempotent; no-op when no 'T' rows exist).

## Capabilities

### New Capabilities
None.

### Modified Capabilities
`db.datetime-storage`: all writers of DateTime columns use the ORM-consistent space-separated format; existing 'T' rows are repaired by migration 011.

## Impact

- Modified: `tracker_app/tools/populate.py`, `tracker_app/tools/preflight_check.py`, `tracker_app/db/migrations.py` (+ migration 011)
- Schema: no table/column changes; data-only normalization.
- Due-query behavior after migration: previously excluded same-day rows become due on the correct day.

## Notes

- The normalization migration is additive and idempotent; it only rewrites text matching the 'T' pattern at position 10, so it cannot touch ORM-written space rows or date-only values.
