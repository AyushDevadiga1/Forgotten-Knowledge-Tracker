# Low-Level Design (LLD)

## 1. Class Structure and Relationships

### 1.1 `track_loop` (Orchestrator in `loop.py`)
- **Role**: The central `while` loop that coordinates polling across all sensors and models. It is completely decoupled from module-level state.
- **Dependencies**: `ActivityMonitor`, `LearningTracker`, `webcam_pipeline`, `audio_module`.
- **Flow**: 
  1. Grabs `window_title` and keyboard/mouse interaction rates.
  2. Submits webcam and OCR tasks to a `ThreadPoolExecutor` for non-blocking analysis.
  3. Blends webcam attention score with interaction rate (CLE).
  4. Triggers `IntentValidator` to predict user state and logs it to `multi_modal_logs`.

### 1.2 `LearningTracker`
- **Role**: Maintains the SM-2 SRS spaced repetition cycle for extracted topics and manual entries.
- **Methods**:
  - `add_learning_item(question, answer, tags)`
  - `record_review(item_id, quality_rating, duration_ms)`: Core SM-2 interval logic block.
  - `get_items_due(limit)`: Retrieves items via `LearningRepository`.

### 1.4 `Repository Layer` (`db/repository.py`)
- **Role**: Decouples business logic modules (`LearningTracker`, `ActivityMonitor`, `api.py`) from SQLAlchemy models and ORM logic.
- **Classes**: `LearningRepository`, `TrackingRepository`, `FeedbackRepository`.
- **Methods**: Contain all raw `db.query(...)` calls for database interaction.

### 1.3 `ActivityMonitor`
- **Role**: Handles raw IO operations and telemetry calculations. 
- **Attributes**: `keyboard_counter`, `mouse_counter` (instances of `ThreadSafeCounter`).
- **Methods**: `get_session_stats()`, `log_session()`.

## 2. API Design & Routing (Flask)
- **`GET /api/v1/learning/items/due`**: Returns memory metrics and due items.
- **`POST /api/v1/learning/items`**: Ingests new manual learning items.
- **`POST /api/v1/learning/reviews`**: Evaluates and advances an item through the SM-2 cycle.
- **`POST /api/v1/intent/feedback`**: Records user corrections and triggers the `FeedbackService` auto-retrainer.

## 3. Database Factory Pattern
- **Lazy Engine Initialization**: The SQLAlchemy Engine and `SessionLocal` are instantiated inside a `get_engine()` lazy factory. This allows tests to override the `FKT_TEST_DB` environment variable without race conditions at module import time. Module-level aliases use a proxy pattern to maintain backward compatibility.
