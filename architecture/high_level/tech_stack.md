# Tech Stack Document

## Programming Language
- **Python 3.11**: Primary orchestration language. Chosen for its rich ecosystem of AI/ML tooling, UI automation, and simple web integrations.

## Core Libraries
- **Flask (3.0.x)** & **Flask-SocketIO**: For lightweight synchronous and asynchronous web endpoints.
- **SQLite3** & **SQLAlchemy**: Inbuilt Python DB managed via an ORM. Chosen because FKT is a local, strictly single-user application.
- **Pillow (10.0+)** & **pytesseract**: For screen grabbing and keyword OCR processing.
- **sounddevice** & **librosa**: For reading microphone buffers and extracting RMS/Energy to detect silence/speech.
- **mediapipe**: To detect user gaze and attention from the webcam using FaceMesh. 
- **pynput**: Keyboard and mouse event listeners.
- **scikit-learn**: Used for the auto-retraining Intent Predictor model.

## Architecture Patterns
- **Monolithic Modularity**: A single entry point (`main.py`) orchestrates distinct directories for `/tracking`, `/learning`, and `/web`, all operating on a shared, unified `/data/fkt_tracking.db` SQLite volume.
- **Hybrid Heuristic/ML Approach**: Intent classification uses a lightweight `RandomForestClassifier` that continuously auto-retrains itself from user feedback. Audio categorization explicitly relies on deterministic mathematical rules.

## Frontend
- **React 18 + TypeScript**: Component-based UI served from `tracker_app/web/frontend/`.
- **Vite**: Development server and build tool (`npm run dev` in the frontend directory).
- **Tailwind CSS**: Utility-first styling; configured via `tailwind.config.js`.
- **Flask-SocketIO**: Real-time push events from backend to frontend (quiz interrupts, live stats).
