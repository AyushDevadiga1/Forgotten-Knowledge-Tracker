# Entity Relationship Diagram (ERD)

The system relies on a local SQLite3 configuration managed through SQLAlchemy. All data is unified into a single database file (`sessions.db`).

The schema is defined by 16 ORM classes in `tracker_app/db/models.py`.

## Review / Learning Tables

### 1. `learning_items`
Stores the active knowledge items to be reviewed via spaced repetition (SM-2).
- `id` (String, PK): Unique identifier.
- `question` (String): The concept/keyword.
- `answer` (String): The context or definition.
- `difficulty` (String): e.g., "medium".
- `item_type` (String): e.g., "concept".
- `tags` (String): Comma-separated tags.
- `interval` (Integer): Days until next review.
- `ease_factor` (Float): SM-2 multiplier for review scaling.
- `repetitions` (Integer): Success streak count.
- `next_review_date` (DateTime, Indexed): Target deadline.
- `last_review_date` (DateTime): Timestamp of the most recent review.
- `total_reviews` (Integer): Total attempts.
- `correct_count` (Integer): Successful attempts.
- `success_rate` (Float): Correct / Total.
- `status` (String, Indexed): "active", "mastered", or "archived".
- `created_at` (DateTime): ISO8601 Timestamp.
- `updated_at` (DateTime): ISO8601 Timestamp.

### 2. `review_history`
Historical log of when learning items were reviewed.
- `id` (Integer, PK, AUTOINCREMENT)
- `item_id` (String, FK): Maps to `learning_items.id`.
- `timestamp` (DateTime, Indexed): ISO8601 Timestamp.
- `quality_rating` (Integer): 0-5 SM-2 quality score.
- `old_interval`, `new_interval` (Integer)
- `old_ease`, `new_ease` (Float)

## Concept Tracking Tables

### 3. `tracked_concepts`
Auto-tracked concepts promoted toward the SM-2 deck.
- `concept` (String, PK)
- `first_seen`, `last_seen` (DateTime, `last_seen` Indexed)
- `frequency_count` (Integer)
- `relevance_score` (Float)
- `context_tags` (String)
- `status` (String): e.g., "discovered".
- `interval` (Integer), `memory_strength` (Float), `next_review` (DateTime, Indexed), `repetitions` (Integer)
- `review_count` (Integer), `correct_count` (Integer)
- `attention_at_encoding` (Float), `lambda_personalised` (Float): AWFC personalisation.

### 4. `concept_encounters`
Each individual encounter of a tracked concept (OCR, browser extension, or manual).
- `id` (Integer, PK, AUTOINCREMENT)
- `concept` (String, FK to `tracked_concepts.concept`, Indexed)
- `timestamp` (DateTime, Indexed)
- `source` (String): "ocr", "browser_extension", or "manual".
- `confidence` (Float)
- `context_snippet` (String)

### 5. `triage_queue`
Concepts awaiting manual approval before promotion to `tracked_concepts`.
- `id` (Integer, PK, AUTOINCREMENT)
- `concept` (String, unique, Indexed)
- `answer` (String)
- `difficulty` (String): e.g., "medium".
- `status` (String): "pending", "approved", or "rejected".
- `frequency_count` (Integer)
- `created_at`, `reviewed_at` (DateTime)

## Session & Telemetry Tables

### 6. `tracking_sessions`
Aggregated session blocks.
- `id` (Integer, PK, AUTOINCREMENT)
- `start_time` (DateTime, Indexed)
- `end_time` (DateTime)
- `duration_minutes` (Float)
- `concepts_encountered` (Integer)
- `avg_attention` (Float)
- `primary_activity` (String)

### 7. `sessions`
System-level session rows with per-cycle telemetry.
- `id` (Integer, PK, AUTOINCREMENT)
- `start_ts` (DateTime, Indexed), `end_ts` (DateTime)
- `app_name`, `window_title` (String)
- `interaction_rate` (Float), `interaction_count` (Integer)
- `audio_label` (String)
- `intent_label` (String), `intent_confidence` (Float)

### 8. `daily_summary`
Per-day rollup of tracking activity.
- `date` (String, PK): "YYYY-MM-DD".
- `total_tracking_minutes` (Float)
- `concepts_encountered` (Integer)
- `avg_attention` (Float)
- `primary_intents` (String)

### 9. `multi_modal_logs`
Periodic snapshot of user context (OCR, Audio, Attention).
- `id` (Integer, PK, AUTOINCREMENT)
- `timestamp` (DateTime, Indexed)
- `window_title` (String)
- `ocr_keywords` (String)
- `audio_label` (String): "speech", "music", "silence".
- `attention_score` (Float)
- `interaction_rate` (Float)
- `intent_label` (String), `intent_confidence` (Float)
- `memory_score` (Float)

### 10. `memory_decay`
Per-keyword decay/recall tracking.
- `id` (Integer, PK, AUTOINCREMENT)
- `keyword` (String, Indexed)
- `last_seen_ts` (DateTime, Indexed)
- `predicted_recall` (Float)
- `observed_usage` (Integer)
- `updated_at` (DateTime)

### 11. `metrics`
Snapshot of per-concept scheduling metrics.
- `id` (Integer, PK, AUTOINCREMENT)
- `concept` (String)
- `next_review_time` (DateTime)
- `memory_score` (Float)
- `last_updated` (DateTime)

## Intent & Feedback Tables

### 12. `intent_predictions`
Logs heuristic/ML intent evaluations.
- `id`, `timestamp` (Indexed), `predicted_intent`, `confidence`, `context_keywords`
- `user_feedback` (1=correct, 0=wrong), `actual_intent`, `feedback_timestamp`
- `prompted_at` (DateTime), `window_title` (String)

### 13. `intent_accuracy`
Aggregated accuracy per intent class.
- `intent` (PK), `total_predictions`, `correct_predictions`, `accuracy`, `last_updated`

### 14. `feedback_training_samples`
Used for background auto-retraining of the intent classifier.
- `id`, `timestamp` (Indexed), `feature_vector` (JSON), `predicted_label`, `actual_label`, `confidence`
- `window_title` (String), `used_in_training` (Integer)

## Configuration / Calibration Tables

### 15. `session_toggle`
Persists the study-session start/stop toggle state (single row, id=1).
- `id` (Integer, PK, default 1)
- `active` (Boolean)
- `started_at`, `stopped_at`, `updated_at` (DateTime)

### 16. `ear_calibration`
Stores the latest webcam EAR calibration baseline (single row, id=1).
- `id` (Integer, PK, default 1)
- `personal_ear_low`, `personal_ear_high`, `mean_ear`, `std_ear` (Float)
- `fallback` (Boolean)
- `raw_data` (String)
- `updated_at` (DateTime)

## Relationships
- `learning_items (id)` -> `review_history (item_id)` : One-to-Many (Cascade Delete).
- `tracked_concepts (concept)` -> `concept_encounters (concept)` : One-to-Many (Cascade Delete).
