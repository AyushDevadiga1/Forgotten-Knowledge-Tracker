# Data Flow Diagram (DFD)

The data flow within the Forgotten Knowledge Tracker follows an Event-Driven periodic ingestion pattern. 

## Context Level (Level 0)
```text
[User] --(Keyboard/Mouse)--> [FKT Tracker]
[Desktop Display] --(Screen)--> [FKT Tracker]
[Environment] --(Microphone/Webcam)--> [FKT Tracker]
[FKT Tracker] --(Periodic Telemetry)--> [Web Dashboard]
```

## Level 1 DFD Component Interactions

1. **Ingestion**
   - The OS fires Keyboard/Mouse events asynchronously into the `ThreadSafeCounter`.
   - Polling Loops execute at defined intervals (e.g., `AUDIO_INTERVAL=15`, `SCREENSHOT_INTERVAL=20`), generating audio NumPy arrays and Pillow Image captures.
2. **Transform**
   - **Audio Array** -> `librosa.feature` -> RMS Energy -> Output "speech"/"music"/"silence".
   - **Pillow Image** -> `pytesseract` -> Output text string -> `TF-IDF Extractor` -> Output top K keywords.
   - **Webcam Image** -> `dlib` -> Eye ratio & pose estimation -> Output integer attention score.
3. **Synthesis**
   - `EnhancedActivityTracker` collates the keywords, the attention score, the audio state, and the interaction rate into an `intent_result` dictionary.
4. **Storage**
   - Extracted concepts are fired to `ConceptScheduler`, executing an SQL `INSERT` or `UPDATE` conditionally.
   - The aggregate session is fired to `TrackingAnalytics` bounding the time frame and average interactions.
5. **Retrieval**
   - User loads the Web Dashboard (`app.py`).
   - `LearningTracker` reads SQLite databases and pushes data to the Jinja templates.
