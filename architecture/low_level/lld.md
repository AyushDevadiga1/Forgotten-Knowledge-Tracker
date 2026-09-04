# Low-Level Design (LLD)

## 1. Class Structure and Relationships

### 1.1 `track_loop` (Orchestrator in `loop.py`)
- **Role**: The central `while` loop that coordinates polling across all sensors and models. It is completely decoupled from module-level state.
- **Dependencies**: `ActivityMonitor`, `predict_intent`, `get_cle`, `session_is_active`, `is_sensitive_window` (module-level imports in `loop.py`); OCR/audio/webcam pipelines are loaded lazily at runtime.
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
- All API routes are organised into nine versioned blueprints, each registered under the `/api/v1` prefix (`web/routes/`, wired in `web/app.py`):
  - **items** (`items.py`): `GET/POST /api/v1/items`, `GET /api/v1/items/due`, `GET/POST/DELETE /api/v1/items/<item_id>`, `POST /api/v1/items/backfill`, `POST /api/v1/items/<item_id>/archive|unarchive`, `GET /api/v1/search`, `GET /api/v1/export`, `GET /api/v1/triage`, `POST /api/v1/triage/<id>/approve|reject`
  - **graph** (`graph.py`): `GET /api/v1/graph/stats`, `POST /api/v1/graph/sync`, `GET /api/v1/graph/gaps`, `GET /api/v1/graph/drift/<concept>`, `GET /api/v1/graph/concept/<concept>`
  - **session** (`session.py`): `POST /api/v1/reviews`, `DELETE /api/v1/concepts/<concept>`, `GET /api/v1/session/status`, `POST /api/v1/session/start|stop|calibrate`
  - **intent** (`intent.py`): `GET /api/v1/intent/recent`, `POST /api/v1/intent/feedback`, `DELETE /api/v1/intent/predictions`, `GET /api/v1/intent/stats`
  - **quiz** (`quiz.py`): `GET /api/v1/quiz/current`, `POST /api/v1/quiz/answer`
  - **stats** (`stats.py`): `GET /api/v1/stats`, `GET /api/v1/stats/trend`, `GET /api/v1/stats/accuracy-today`, `DELETE /api/v1/tracking/history`, `GET /api/v1/tracking/daily-summary`, `GET /api/v1/tracking/trend-analysis`
  - **telemetry** (`telemetry.py`): `GET /api/v1/telemetry/summary`
  - **ingest** (`ingest.py`): `POST /api/v1/ingest`
  - **health** (`health.py`): `GET /api/v1/health` (deliberately left unauthenticated)


## 3. Database Factory Pattern
- **Lazy Engine Initialization**: The SQLAlchemy Engine and `SessionLocal` are instantiated inside a `get_engine()` lazy factory. This allows tests to override the `FKT_TEST_DB` environment variable without race conditions at module import time. Module-level aliases use a proxy pattern to maintain backward compatibility.
