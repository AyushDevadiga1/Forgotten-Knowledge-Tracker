## 1. Drop the duplicate index

- [x] 1.1 `tracker_app/db/migrations.py`: append migration `012_drop_duplicate_feedback_index` with `DROP INDEX IF EXISTS ix_feedback_samples_timestamp`

## 2. Regression coverage

- [x] 2.1 Test: fresh migrated DB has exactly one index on feedback_training_samples(timestamp) — `ix_feedback_training_samples_timestamp`
- [x] 2.2 Test: already-duplicate DB (both indexes) converges to one after `run_migrations`
- [x] 2.3 Run `venv\Scripts\python.exe -m pytest tracker_app/tests -q` and confirm full suite green

## 3. Coordination

- [x] 3.1 Apply after normalize-datetime-storage-format (011); do not renumber 011
