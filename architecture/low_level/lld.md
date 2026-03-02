# Low-Level Design (LLD)

## 1. Class Structure and Relationships

### 1.1 `EnhancedActivityTracker` (orchestrator)
- **Role**: Coordinates the overall tracking loops and manages thread safety across events.
- **Attributes**: `session_start`, `session_concepts`, `session_attention_scores`, `is_running`.
- **Dependencies**: `ConceptScheduler`, `ActivityMonitor`, `IntentValidator`, `TrackingAnalytics`.
- **Methods**: 
  - `start_session()` / `end_session()`: Modifies tracking loop state.
  - `process_concepts(ocr_keywords, confidence)`: Delegates to `ConceptScheduler`.
  - `process_intent(intent_result, context)`: Delegates to `IntentValidator`.

### 1.2 `ConceptScheduler`
- **Role**: Maintains the SM-2 SRS spaced repetition cycle for extracted topics.
- **Attributes**: `db_path`.
- **Methods**:
  - `add_concept(concept, confidence, context)`
  - `schedule_next_review(concept_id, quality)`: Core SM-2 logic block.
  - `get_due_concepts(limit)`: SQLite interaction for fetching matured rows.

### 1.3 `ActivityMonitor`
- **Role**: Handles raw IO operations and telemetry calculations.
- **Attributes**: `keyboard_counter`, `mouse_counter` (instances of `ThreadSafeCounter`).
- **Methods**: `get_session_stats()`.

## 2. API Design & Routing (Flask)
- **`GET /stats`**: Returns memory metrics and recent interactions.
- **`GET /search?q={query}`**: Triggers DB text search.
- **`POST /add`**: Ingests new user-defined manual learning items.
- **`GET/POST /review/<item_id>`**: Evaluates and advances an item through the SM-2 cycle.

## 3. Worker Threads
- **pynput kb/mouse Listeners**: Run natively in the background, interacting exclusively with locked counters.
- **Flask SocketIO**: Handles real-time client side data push without blocking the UI rendering threads.
