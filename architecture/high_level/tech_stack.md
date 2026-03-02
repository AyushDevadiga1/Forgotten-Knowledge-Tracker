# Tech Stack Document

## Programming Language
- **Python 3.11**: Primary orchestration language. Chosen for its rich ecosystem of AI/ML tooling, UI automation, and simple web integrations.

## Core Libraries
- **Flask (3.0.x)** & **Flask-SocketIO**: For lightweight synchronous and asynchronous web endpoints.
- **SQLite3**: Inbuilt Python DB. Chosen because FKT is a local, strictly single-user application that does not warrant a remote SQL host.
- **Pillow (10.0+)** & **pytesseract**: For screen grabbing and keyword OCR processing.
- **sounddevice** & **librosa**: For reading microphone buffers and extracting RMS/Energy to detect silence/speech.
- **opencv-python** & **dlib**: To detect user gaze and attention from the webcam. 
- **pynput**: Keyboard and mouse event listeners.

## Architecture Patterns
- **Monolithic Modularity**: Distinct directories for `/core`, `/web`, and `/scripts` but operating on a shared `/data` volume.
- **Heuristic Fallbacks**: Intent and audio categorization now explicitly rely on deterministic mathematical rules rather than black-box AI models to ensure transparency and efficiency.

## To-Be-Configured (Frontend)
- The frontend tech stack is pending modernization. Expected to use vanilla JS + modern CSS frameworks.
