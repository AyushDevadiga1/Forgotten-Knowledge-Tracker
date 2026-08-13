# Context pack: FKT-F-003 — learning_items.last_review_date unmapped column

## Candidate statement (exact)
"Schema-model drift: the column exists in migrated DBs but the ORM model neither maps nor writes it. API row serialization always returns last_review_date: null even after reviews; SM-2 retention estimate loses last-review time across restarts. Writing it via the ORM is impossible (attribute missing → AttributeError)."

## Contract evidence
- migrations.py:82-85 — `005_learning_item_last_review`: "Add last_review_date to learning_items" (comment "was missing" — the column was intended FOR the model).
- models.py:122-149 — `LearningItem` declares next_review_date (:136) but NO last_review_date attribute.
- models.py:335 class FeedbackTrainingSample comment style aside — model docs elsewhere show columns are documented in-model.
- Defensive papering: learning_tracker.py:270 `getattr(row, 'last_review_date', None)`; :300-301 `item_dict.get('last_review_date')`.

## Source locations (minimal)
- tracker_app/db/migrations.py:82-85 (005 ADD COLUMN last_review_date TEXT).
- tracker_app/db/models.py:122-149 (LearningItem; no last_review_date).
- tracker_app/learning/learning_tracker.py:254-276 (`_row_to_dict`, :270 getattr→None), :278-305 (`_dict_to_sm2item`, :300-301 always-None read).
- tracker_app/learning/sm2_memory_model.py:59 (`last_review_date = None` init), :130 (`item.last_review_date = datetime.utcnow()` in-memory only), :161-177 (`estimate_retention` returns zeros when None; :170 uses it).
- API consumer: web/api.py `/items` serialization flows through `_row_to_dict`.

## Reproduction (temp DB; live DB read-only)
1. Fresh-schema probe: `$env:FKT_TEST_DB='C:\Users\hp\AppData\Local\Temp\opencode\f003.db'`; run `venv\Scripts\python.exe -c "from tracker_app.db.db_module import init_db; init_db()"`, then check `PRAGMA table_info(learning_items)` via sqlite3 → no last_review_date (create_all path has no column).
2. Migrated-schema probe: `$env:FKT_TEST_DB='C:\Users\hp\AppData\Local\Temp\opencode\f003_m.db'`; `venv\Scripts\python.exe -m tracker_app.db.migrations`; then ORM insert `LearningItem(...)` and attempt `item.last_review_date = datetime.utcnow()` → AttributeError (model has no attribute).
3. Serialization probe: `LearningTracker._row_to_dict(item)` → `'last_review_date': None` even immediately after an SM2 review.
4. Live read-only: `SELECT COUNT(*) FROM learning_items WHERE last_review_date IS NOT NULL` on tracker_app/data/sessions.db → 0; `PRAGMA table_info(learning_items)` shows the column (drift confirmed on real data).

## Assertion points
- Column presence differs by init path (create_all vs migrations).
- `AttributeError` on ORM attribute write; `getattr` returns None; `estimate_retention` all-zeros when last_review_date None.
- Live DB: column exists, 0 non-null values.

## Traps
- Live DB: read-only SELECT/PRAGMA only; never run migrations or writes against tracker_app/data/sessions.db.
- Do not count the F-002 angle (startup never runs migrations) as proof here — separate candidate; for F-003 use explicit `-m tracker_app.db.migrations` on the temp DB.
- `run_migrations`/`python -m tracker_app.db.migrations` require FKT_TEST_DB set, else they migrate the real DB.

## Unresolved
- Fix direction (map+persist on review vs drop column/migration); check frontend/API consumers of last_review_date before choosing.
