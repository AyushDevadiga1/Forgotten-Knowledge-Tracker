# High-Level Design (HLD)

## 1. System Components
At a high level, the system comprises the following components:
1. **OS Sensor Layer**: Libraries hooking into mouse/keyboard (`pynput`), screen recording (`pytesseract`), microphone (`sounddevice`), and webcam (`cv2`).
2. **Analysis Pipelines**: 
   - **Audio Pipeline**: Determines if speech, music, or silence is occurring via RMS energy falling back on librosa heuristics. 
   - **OCR Pipeline**: Periodically checks the screen and extracts top TF-IDF keywords.
   - **Webcam Pipeline**: Determines gaze orientation using `dlib` facial landmarks.
3. **Intent & Concept Engine**: Cross-references signals at a defined interval (e.g., 5 seconds) to assign an action Intent ("idle", "passive", "studying") and extract active concepts.
4. **Storage Layer**: SQLite stores periodic telemetry, concept metrics, and session timelines.
5. **Dashboard Layer**: Flask serves REST and WebSocket endpoints for querying memory decay over time.

## 2. Integrations
Currently, all components are natively self-contained. The OCR relies on the externally installed standard `tesseract` binary. Otherwise, everything is maintained locally via SQLite databases.

## 3. Deployment
- The system runs natively as two standalone python processes (`run_tracker.py` and `run_dashboard.py` / `waitress` overlay).
