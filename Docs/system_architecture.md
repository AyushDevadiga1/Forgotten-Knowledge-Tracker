# System Architecture Document (SAD)

## 1. Overview
The Forgotten Knowledge Tracker (FKT) is a productivity and learning companion tool that observes a user's digital context (screen content, input interaction, spoken audio, facial attention) to organically identify concepts they are learning. It schedules intelligent reviews of these concepts using an SM-2 spaced repetition memory model.

## 2. High-Level Architecture
FKT employs a local-first, background-agent architecture divided into two primary subsystems:
1. **Background Tracker (`tracker_app/core/`)**: Collects multi-modal telemetry (OCR, Audio, Webcam, Input rates).
2. **Web Dashboard (`tracker_app/web/`)**: A Flask-based lightweight HTTP and WebSocket server presenting stats and scheduled reviews to the user.

Both subsystems share a local SQLite data layer to ensure robust state management across sessions.

## 3. Technology Choices
- **Backend & Orchestration**: Python 3.11+
- **Database**: SQLite3 (Local, lightweight, zero-configuration)
- **Web Server**: Flask + Flask-SocketIO
- **UI/Frontend**: (Pending redesign) Native HTML/JS/CSS 
- **OCR**: Tesseract + Pillow
- **Audio Processing**: Sounddevice + librosa (RMS energy thresholding)
- **Webcam Tracking**: OpenCV + dlib for facial pose / attention

## 4. Components
- `EnhancedActivityTracker`: Coordinates polling from input listeners, audio pipeline, webcam, and OCR.
- `ConceptScheduler`: Employs SM-2 algorithms to plan knowledge retention schedules.
- `ActivityMonitor`: Logs interaction tracking.
- `LearningTracker`: Provides the CRUD business logic interface for the web dashboard.
