# High-Level Design (HLD)

## 1. System Components
At a high level, the system comprises the following components:
1. **OS Sensor Layer**: Libraries hooking into mouse/keyboard (`pynput`), screen recording (`pytesseract`), microphone (`sounddevice`), and webcam (`cv2`).
2. **Analysis Pipelines**: 
   - **Audio Pipeline**: Determines if speech, music, or silence is occurring via RMS energy falling back on librosa heuristics. 
   - **OCR Pipeline**: Periodically checks the screen and extracts top TF-IDF keywords.
   - **Webcam Pipeline**: Determines gaze orientation and attention using `mediapipe` facial landmarks (FaceMesh).
3. **Intent & Concept Engine**: Cross-references signals at a defined interval (e.g., 5 seconds) to assign an action Intent ("idle", "passive", "studying") and extract active concepts.
4. **Storage Layer**: A unified SQLite database (`fkt_tracking.db`) via SQLAlchemy stores periodic telemetry, concept metrics, and session timelines.
5. **Dashboard Layer**: Flask serves REST and WebSocket endpoints for querying memory decay over time.

## 2. Integrations
Currently, all components are natively self-contained. The OCR relies on the externally installed standard `tesseract` binary. Otherwise, everything is maintained locally via the unified SQLite database.

## 3. Deployment
- The system runs natively from a single unified entrypoint: `main.py`. This spawns the backend dashboard and the tracking loops together in a coordinated multi-threaded environment.
