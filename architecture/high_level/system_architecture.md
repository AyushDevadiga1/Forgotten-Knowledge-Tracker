# System Architecture Document (SAD)

## 1. Overview
The Forgotten Knowledge Tracker (FKT) is a productivity and learning companion tool that observes a user's digital context (screen content, input interaction, spoken audio, facial attention) to organically identify concepts they are learning. It schedules intelligent reviews of these concepts using an SM-2 spaced repetition memory model.

## 2. High-Level Architecture
FKT employs a local-first, background-agent architecture divided into two primary subsystems:
1. **Background Tracker (`tracker_app/tracking/`)**: Collects multi-modal telemetry (OCR, Audio, Webcam, Input rates).
2. **Web Dashboard (`tracker_app/web/`)**: A Flask-based lightweight HTTP and WebSocket server presenting stats and scheduled reviews to the user.

Both subsystems are orchestrated via `main.py` and share a local SQLAlchemy SQLite data layer to ensure robust state management across sessions.

## 3. Technology Choices
- **Backend & Orchestration**: Python 3.11+
- **Database**: SQLite3 via SQLAlchemy (Local, lightweight, zero-configuration)
- **Web Server**: Flask + Flask-SocketIO
- **UI/Frontend**: (Pending redesign) Native HTML/JS/CSS 
- **OCR**: Tesseract + Pillow
- **Audio Processing**: Sounddevice + librosa (RMS energy thresholding)
- **Webcam Tracking**: Mediapipe FaceMesh for facial pose / attention

## 4. Components
- **`track_loop`**: The central loop in `loop.py` that coordinates polling from input listeners, audio pipeline, webcam, and OCR.
- **`LearningTracker`**: Maintains the SM-2 SRS spaced repetition cycle and coordinates with the data layer.
- **`ActivityMonitor`**: Logs interaction tracking and records user sessions.
- **`FeedbackService`**: Manages user corrections to AI predictions and orchestrates background auto-retraining.
- **`Repository Layer` (`db/repository.py`)**: Centralizes all SQLAlchemy data access logic (CRUD, aggregations) to fully decouple the business logic from the ORM.
