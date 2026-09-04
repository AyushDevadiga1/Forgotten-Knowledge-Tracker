<div align="center">

# 🧠 Forgotten Knowledge Tracker (FKT)

**FKT is your silent study companion. It watches what you study, remembers what you tend to forget, and quizzes you before it happens — automatically.**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Active Development](https://img.shields.io/badge/status-active%20development-green.svg)]()
[![Platform: Windows](https://img.shields.io/badge/platform-Windows%20(primary)-lightgrey.svg)]()

*No note-taking. No making your own flashcards. You just press **Start** when you study — FKT handles the rest.*

</div>

---

## What it is

FKT is a **desktop program** that runs in the background on your computer, learns what you study from your screen, and schedules short review moments so you do not forget. You only ever press one button — Start Studying — and everything else is automatic.

It is based on the same research-proven **spaced repetition** idea used by popular learning apps (like Anki). The key difference: **FKT fills itself from your real study activity** instead of making you type in cards by hand.

---

## What problem does it solve?

You know this feeling: you study something, understand it completely, then two weeks later... it is gone. Forgetting is normal — our brains are designed to let unused information fade.

FKT works with your brain instead of against it. Because it sees *what* you studied and *how focused* you were at the time, it can predict when a particular idea is about to fade from memory — and remind you of it **just before** it does. A five-second review at the right time saves you a re-study session later.

---

## How does it work? (Without the jargon)

1. **You decide when to start.** FKT only watches while a study session is active. Press **Start Studying** when you begin; no session, no watching.
2. **It pays attention to your screen.** Every so often it quietly looks at the window you are working in (not your whole screen) and picks out the key words and ideas.
3. **It senses how focused you are.** It can use your microphone to tell if you are in a quiet room or a noisy environment, and your webcam (optional) to see whether you look engaged or tired. It also watches your typing rhythm — people type differently when they are deeply concentrating.
4. **It decides what is worth remembering.** If you are clearly studying, it keeps the ideas it saw. If you get distracted, it ignores that.
5. **It builds your personal knowledge map.** Related ideas get connected together, so FKT knows the *shape* of what you know.
6. **It schedules the right moment to remind you.** Using a well-known memory-science algorithm, FKT decides when each idea needs a quick refresher — then pops a tiny quiz during an idle moment.

| What it watches | What it learns from it |
|---|---|
| Your screen (the active window only) | The words and ideas you are studying |
| Your microphone | Whether the environment is quiet or noisy |
| Your webcam *(optional)* | Whether you look focused or drowsy |
| Your typing rhythm | How deeply you are concentrating |

---

## Features

- **Screen capture → OCR → keywords** — the active window is analysed and the key ideas are extracted automatically.
- **Audio idle/study detection** — knows whether the room is quiet or noisy.
- **Optional webcam attention (EAR)** — detects focus and drowsiness.
- **Keystroke (CLE) engagement** — estimates cognitive load from typing dynamics without a camera.
- **SM-2 spaced repetition + AWFC decay** — schedules reviews and personalises the decay rate from your attention.
- **Knowledge graph** — related concepts are linked into a personal semantic map.
- **Browser extension ingest** — capture concepts from your browsing sessions too.
- **Triage queue** — captured concepts are reviewed before they reach your learning deck.
- **Contextual micro-quiz interrupts** — generated from your own content and fed back into SM-2.

---

## How it works (system view)

```
Your screen  ──► OCR (Tesseract)  ──►┐
Your mic     ──► Audio classify   ──►│
Your webcam  ──► EAR attention    ──►├──► Feature vector ──► Intent classifier
Your keyboard──► CLE estimation   ──►│        │                    │
                                     │        │                    ▼
                                     │        │         studying / passive / idle
                                     │        ▼
                                     │   YAKE! keyword extraction
                                     │        │
                                     │        ▼
                                     │   Knowledge Graph update
                                     │   (concept nodes + semantic edges)
                                     │        │
                                     │        ▼
                                     │   Ebbinghaus AWFC scoring
                                     │   (λ adjusted by attention at encoding)
                                     │        │
                                     │        ▼
                                     └──► SM-2 scheduling ──► Review reminders
```

Every 5 seconds, FKT's tracking loop runs one cycle. OCR runs every 20 s, audio every 15 s, webcam every 45 s. All pipelines are lazy-loaded and run asynchronously so the loop never blocks. The loop idles (no capture at all) whenever no study session is active.

---

## Your privacy

Privacy is a core design choice, not an afterthought:

- **Nothing leaves your computer.** Everything runs locally. No account, no cloud, no uploads — FKT never sends data anywhere.
- **Sensitive info is removed automatically.** Credit card numbers, emails, passwords, and similar details are detected and scrubbed before anything is saved.
- **Private windows are skipped.** Windows with titles like “password”, “login”, or “bank” are never looked at.
- **You stay in control.** FKT only watches while a study session is active — flip the switch off and it goes fully quiet.
- **Your data is a file you own.** Everything is stored in a single database file on your machine. Delete it any time; nothing is hidden.

## Getting started

For a non-technical try-out you will still need one terminal command — that is the whole story:

```
python setup.py --run
```

That single command installs everything, then starts the program. Open your browser to **http://localhost:5000** and press **Start Studying**.

`setup.py` handles the whole bootstrap:
1. Creates a clean `venv/` and installs all dependencies.
2. Auto-downloads and silently installs Tesseract OCR (Windows only).
3. Creates `.env` from the example if it does not exist.
4. Initialises the SQLite database.
5. *(with `--run`)* Starts both the background tracker and the web dashboard.

### Manual start (advanced)

```bash
.\venv\Scripts\activate          # Windows
source venv/bin/activate         # Linux/macOS

python -m tracker_app.main       # Background tracker (asks about webcam on start)

python -m tracker_app.web.app    # In a second terminal -> http://localhost:5000
```

---

## Configuration

All settings live in `.env` (created automatically by `setup.py`). Sensible defaults are shown.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(auto-generated)* | Flask session secret — set a strong one in production |
| `API_KEY` | *(auto-generated)* | Enforces `X-API-Key` on `/api/v1` when set |
| `NO_AUTH` | `false` | Set `true` to disable API-key auth in local dev |
| `DEBUG` | `True` | Flask debug mode |
| `TESSERACT_PATH` | *(auto-detected)* | Path to the Tesseract executable |
| `DATABASE_URL` | `sqlite:///tracker_app/data/sessions.db` | SQLAlchemy database URL |
| `TRACK_INTERVAL` | `5` | Main loop interval (seconds) |
| `SCREENSHOT_INTERVAL` | `20` | How often to run OCR (seconds) |
| `AUDIO_INTERVAL` | `15` | How often to classify audio (seconds) |
| `WEBCAM_INTERVAL` | `45` | How often to check eye-tracking (seconds) |
| `ALLOW_WEBCAM` | `true` | Enable webcam by default |
| `SESSION_ALLOWED_INTENTS` | `studying` | Intent labels allowed to persist concepts in an active session |
| `INTENT_TOAST_COOLDOWN_MINUTES` | `5` | Cooldown between intent-feedback prompts |
| `OCR_MIN_WORD_CONFIDENCE` | `30` | Minimum OCR word confidence to keep |

---

## Architecture

FKT is a **local-first, monolithic-modular** application with a single Python entry point (`main.py`) that orchestrates distinct subsystems sharing one SQLite database:

- **`tracker_app/tracking/`** — sensing and signal processing (OCR, audio, webcam, CLE, intent, knowledge graph, privacy).
- **`tracker_app/learning/`** — memory science (SM-2, AWFC, concept scheduling).
- **`tracker_app/db/`** — SQLAlchemy models and data access.
- **`tracker_app/web/`** — Flask + Socket.IO dashboard and a React 18 + TypeScript + Vite SPA frontend.

The API is organised into nine versioned blueprints under `/api/v1` (`tracker_app/web/routes/`). An interactive map of every function is available at [docs/dependency-map/index.html](docs/dependency-map/index.html) (double-click to open — no server needed). Detailed design docs live in [`architecture/`](architecture/).

---

## Development

```bash
# Install dependencies
python setup.py

# Run the backend test suite (407 tests)
.\venv\Scripts\activate
python -m pytest tracker_app/tests/

# Run the frontend dev server (React + Vite)
cd tracker_app/web/frontend
npm install
npm run dev

# Regenerate the function dependency map after code changes
python tools/generate_dependency_map.py
```

---

## Retraining the Intent Model

The intent classifier ships trained on synthetic data. To retrain (e.g., after collecting real feedback):

```bash
python -m tracker_app.scripts.train_models_from_logs
```

This loads existing training data (or generates a fresh 2,500-sample synthetic dataset), trains a RandomForest with 5-fold cross-validation, prints the report, and saves the model to `models/intent_classifier.pkl`. Restart the tracker to pick it up.

---

## Troubleshooting / FAQ

**App won't start / crashes immediately**
```bash
python setup.py                       # idempotent — just re-run it
python -m tracker_app.config          # prints config and validates paths
```

**Tesseract not found**
```bash
python setup.py --skip-deps           # re-runs the Tesseract check/install only
```
Or install manually from the [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) page and set `TESSERACT_PATH` in `.env`.

**Dashboard shows blank / 500 error**
The React frontend needs to be built:
```bash
cd tracker_app/web/frontend
npm install && npm run build
```

**High CPU usage**
Increase the intervals in `.env` (e.g. `SCREENSHOT_INTERVAL=40`, `AUDIO_INTERVAL=30`, `WEBCAM_INTERVAL=90`).

---

## Novel Contributions

FKT introduces several ideas not found in existing knowledge-management or spaced-repetition systems:

**Cognitive Load Estimator (CLE)** — estimates mental engagement from keystroke dynamics (inter-key interval entropy, typing speed variance, backspace rate, pause density, burst length) without a camera. Based on Epp et al. (2011) and Vizer et al. (2009).

**Attention-Weighted Forgetting Curve (AWFC)** — adjusts the Ebbinghaus decay constant λ based on your attention at the moment a concept was first encountered. Concepts learned during high-focus sessions decay up to 30% slower.

**Cross-Session Concept Drift Detection** — tracks how your understanding of each concept evolves across weeks using Jaccard distance on semantic co-occurrence, surfacing stagnant or regressing concepts.

**Knowledge Gap Mapping** — uses graph traversal to identify concepts adjacent to your existing knowledge but not yet in your graph.

**Micro-Quiz Interrupts** — automatically generates contextual quiz questions from your own captured content during idle periods, feeding results back into SM-2.

---

## Roadmap

**Completed:** core tracking loop, ML pipeline, DB, AWFC, audio, knowledge graph, quiz interrupt, performance work, browser extension ingest, and the React frontend; plus API-key auth, CSRF protection, rate limiting, privacy filtering, and the extraction pipeline.

**Next priorities**
1. Richer quiz types (cloze, typed recall, fill-in-the-blank).
2. Bidirectional concept-deck sync.
3. Deeper dashboard visualisations for attention and study timeline.

---

## Academic Background

FKT was developed as a final-year B.E. project in Computer Science (AI/ML) at Bharat College of Engineering, Mumbai (2024–25). It integrates:

- **Ebbinghaus forgetting curve** (1885) — mathematical model of memory decay
- **SuperMemo-2 algorithm** (Wozniak, 1987) — research-validated spaced repetition
- **YAKE!** (Campos et al., 2020) — unsupervised single-document keyword extraction
- **Keystroke dynamics** (Epp et al., 2011; Vizer et al., 2009) — cognitive load from typing patterns
- **MediaPipe FaceMesh** — real-time facial landmark detection for EAR computation

---

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Make your changes and add tests.
4. Run the test suite: `python -m pytest tracker_app/tests/`.
5. Submit a pull request.

Please read `architecture/adr/` before contributing to understand what is built and planned.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built for the ambitious learner.**
*Session-gated capture. Scientific scheduling. Zero manual effort.*

</div>
