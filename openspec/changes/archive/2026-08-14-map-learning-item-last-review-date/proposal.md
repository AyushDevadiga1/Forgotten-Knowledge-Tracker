## Why

Confirmed audit finding FKT-F-003: migration 005 (migrations.py:82-85) added `learning_items.last_review_date` but the `LearningItem` model never maps it, so the ORM cannot write or read it. Consumers read it defensively (`learning_tracker.py:270` `getattr(row, 'last_review_date', None)`) so the API surface always serializes `last_review_date: null` even after reviews, and the SM-2 last-review timestamp computed in memory (`sm2_memory_model.py:130`) is never persisted — retention estimates collapse to 0.0 after a reload. Reproduced end-to-end; live DB has the column with 0 non-null rows.

## What Changes

- `tracker_app/db/models.py`: add `last_review_date = Column(DateTime, nullable=True)` to `LearningItem` (matches the migration-005 column).
- `tracker_app/learning/learning_tracker.py` `record_review`: persist `item_record.last_review_date = review_date` on both the sm2 and leitner paths; keep `_row_to_dict` returning the field (now real data).

## Capabilities

### New Capabilities
None.

### Modified Capabilities
`learning.learning-item`: the review pipeline persists and surfaces `last_review_date`; SM-2 retention state survives reloads.

## Impact

- Modified: `tracker_app/db/models.py`, `tracker_app/learning/learning_tracker.py`
- Schema: no DDL change needed — the column already exists via migration 005 on migrated DBs and `create_all` will create it on fresh DBs.
- API surface: `last_review_date` transitions from always-null to the actual last review time (intended behavior of the column).

## Notes

- Alternative direction (drop the column) rejected: the migration intentionally added it ("was missing", migrations.py:82) and the SM-2 model already computes the value; mapping + persisting restores the intended data path.
