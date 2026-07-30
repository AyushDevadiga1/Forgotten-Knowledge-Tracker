# Entity Relationship Diagram (ERD)

The system relies on a local SQLite3 configuration managed through SQLAlchemy. All data is unified into a single database file (`fkt_tracking.db`).

## Main Tables

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
- `duration_ms` (Integer): How long the user took to answer.

### 3. `tracking_sessions`
Aggregated session blocks.
- `id` (Integer, PK, AUTOINCREMENT)
- `start_time` (DateTime)
- `end_time` (DateTime)
- `duration_minutes` (Float)
- `concepts_encountered` (Integer)
- `avg_attention` (Float)
- `primary_activity` (String)

### 4. `multi_modal_logs`
Periodic snapshot of user context (OCR, Audio, Attention).
- `id` (Integer, PK, AUTOINCREMENT)
- `timestamp` (DateTime)
- `keyboard_events`, `mouse_events` (Integer)
- `active_window` (String)
- `audio_state` (String): "speech", "music", "silence".
- `attention_score` (Float)
- `extracted_text` (String)

### 5. Intent ML Tables (Phase 9)
- **`intent_predictions`**: Logs heuristic/ML intent evaluations.
  - `id`, `timestamp`, `predicted_intent`, `confidence`, `context_keywords`, `user_feedback` (1=correct, 0=wrong), `actual_intent`, `feedback_timestamp`.
- **`intent_accuracy`**: Aggregated accuracy per intent class.
  - `intent` (PK), `total_predictions`, `correct_predictions`, `accuracy`, `last_updated`.
- **`feedback_training_samples`**: Used for background auto-retraining.
  - `id`, `timestamp`, `feature_vector`, `predicted_label`, `actual_label`, `confidence`.

### Relationships
- `learning_items (id)` -> `review_history (item_id)` : One-to-Many (Cascade Delete).
