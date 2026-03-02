# Entity Relationship Diagram (ERD)

The system relies on a local SQLite3 configuration split broadly internally between distinct files (e.g. `tracking_concepts.db`, `sessions.db`). For conceptual simplicity, they operate as distinct entities.

## Main Tables

### 1. `tracked_concepts`
Stores the active knowledge items to be reviewed via spaced repetition.
- `id` (TEXT, PK): Unique identifier.
- `concept` (TEXT, UNIQUE): The keyword/topic.
- `first_seen` (TEXT): ISO8601 Timestamp.
- `last_seen` (TEXT): ISO8601 Timestamp.
- `encounter_count` (INTEGER): Total times recognized.
- `sm2_interval` (REAL): Days until next review.
- `sm2_ease` (REAL): Multiplier for review scaling.
- `next_review` (TEXT): ISO8601 Target deadline.
- `relevance_score` (REAL): 0.0 to 1.0 confidence value.
- `priority` (INTEGER): Manual user override logic.

### 2. `concept_encounters`
Historical log of when and where concepts were discovered.
- `id` (INTEGER, PK, AUTOINCREMENT)
- `concept_id` (TEXT, FK): Maps to `tracked_concepts(id)`
- `timestamp` (TEXT): ISO8601 Timestamp
- `context` (TEXT): e.g. "ocr", "manual"
- `confidence` (REAL): Detection confidence.

### 3. `tracking_sessions`
Aggregated session blocks.
- `id` (INTEGER, PK, AUTOINCREMENT)
- `start_time` (TEXT)
- `end_time` (TEXT)
- `duration_minutes` (REAL)
- `concepts_encountered` (INTEGER)
- `avg_attention` (REAL)
- `primary_activity` (TEXT)

### 4. `intent_predictions`
Log of heuristic intent evaluations.
- `id` (INTEGER, PK, AUTOINCREMENT)
- `timestamp` (TEXT)
- `predicted_intent` (TEXT): 'idle', 'passive', 'studying'.
- `confidence` (REAL)
- `context_keywords` (TEXT)
- `user_feedback` (INTEGER)
- `feedback_timestamp` (TEXT)

### Relationships
- `tracked_concepts (id)` -> `concept_encounters (concept_id)` : One-to-Many.
