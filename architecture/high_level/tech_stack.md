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

## To-Be-Configured (Frontend)
- The frontend tech stack is pending modernization. Expected to use vanilla JS + modern CSS frameworks.
