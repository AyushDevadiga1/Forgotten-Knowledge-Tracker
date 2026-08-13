# FKT-OBS-001 — Out-of-scope observations from the db.models cycle (recorded for future cycles)

- ID: FKT-OBS-001
- STATUS: OPEN (not reproduced this cycle — outside tracker_app.db.models scope)
- SEVERITY: varies
- SCOPE: learning/ + tracking/ layers (consumer logic feeding the models)

## O1 (MEDIUM): Leitner review path never updates interval/ease_factor — stale persisted scheduling state
- LOCATION: tracker_app/learning/sm2_memory_model.py:212-245 (LeitnerSystem.advance_card sets repetitions/next_review_date/total_reviews/correct_count but NOT interval/ease_factor); tracker_app/learning/learning_tracker.py:129-131,138-139 persist item.interval / item.ease_factor (stale).
- CLAIM: after a Leitner review, learning_items.interval stays at the pre-review value while next_review_date jumps by the box interval (1/3/7/14/30); review_history.new_interval/new_ease record stale values. A later SM-2 review computes round(interval*ease) from the stale base (sm2_memory_model.py:127).
- Evidence: code reading (logic-hunter H3). Not reproduced this cycle.

## O2 (LOW): /intent/recent only inspects newest prediction, never re-surfaces older eligible rows
- LOCATION: tracker_app/web/api.py:406-412 + repository.get_recent_intent_prediction (repository.py:205-206).
- Claim: newest-then-reject can starve older never-prompted rows. Mitigated in practice (new rows every ~5 s).

## O3 (LOW): after_flush global logger — fires for every Session incl. tests; cascade deletes not logged (DB-level with passive_deletes=True) contradicting the models.py:102-104 "exactly what records were deleted" comment; eager f-string repr cost.
- No crash reproduced (SQLAlchemy 2.0.51).

## O4 (LOW): LearningItem.id String PK without default → IntegrityError on id-less insert (probe-confirmed); all in-tree callers supply uuid4() → latent contract trap only.
- REJECTED as observable defect for this cycle; noted.

## O5 (LOW): Timezone-aware datetime bound to DateTime column silently stored as naive (probe-confirmed); all in-tree writers use naive utcnow() → latent.
- REJECTED as observable defect for this cycle; noted.

## O6 (LOW): NULL next_review_date / next_review rows silently never due (<= excludes NULL; probe-confirmed); all in-tree writers set it → latent.
- REJECTED as observable defect for this cycle; noted.

## O7 (LOW): Five write-orphaned tables (daily_summary, sessions/SystemSession, multi_modal_logs, memory_decay, metrics) — no producers, only seed tools and delete routes.
- No runtime failure; contract risk only.

## O8 (LOW): FK cascade (passive_deletes=True + ondelete=CASCADE) works only when PRAGMA foreign_keys=ON is set by the production engine; test engines without the pragma leave orphan children. Production OK.
- REJECTED for this cycle.

## O9 (LOW): Missing DB parent directory surfaces as opaque "unable to open database file" for direct SessionLocal consumers that skip init_db().
- Error-quality only.
