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

## What is FKT? (In plain English)

Imagine you had a **personal librarian** who:

1. Watches over your shoulder (only while you allow it) while you study on your computer.
2. Quietly takes note of the important words and ideas you come across.
3. Keeps track of which ideas you seem to struggle with.
4. Later, at the right moment, asks you a quick question to make sure the idea stays in your head.

That librarian is FKT. It is a **desktop program** that runs in the background on your own computer, learns what you are studying from your screen, and schedules short review moments so you do not forget.

It is based on the same research-proven "spaced repetition" idea used by popular learning apps (like Anki) — the key difference is that **FKT fills itself from your real study activity instead of making you type in cards by hand**.

---

## What problem does it solve?

You know this feeling: you study something, understand it completely, then two weeks later... it is gone. Forgetting is normal — our brains are designed to let unused information fade.

FKT works with your brain instead of against it. Because it sees *what* you studied and *how focused* you were at the time, it can predict when a particular idea is about to fade from memory — and remind you of it **just before** it does. A five-second review at the right time saves you a re-study session later.

---

## How does it work? (Without the jargon)

Here is what happens, step by step:

1. **You decide when to start.** FKT only watches while a study session is active. Press **Start Studying** when you begin; it stops when you press **Stop**. No session, no watching.

2. **It pays attention to your screen.** Every so often it quietly looks at the window you are working in (not your whole screen) and picks out the key words and ideas.

3. **It senses how focused you are.** It can use your microphone to tell if you are in a quiet room or in a noisy environment, and your webcam (optional) to see whether you look engaged or tired. It also watches your typing rhythm — people type differently when they are deeply concentrating.

4. **It decides what is worth remembering.** If you are clearly studying (reading a textbook, writing notes), it keeps the ideas it saw. If you get distracted (a chat message, a video), it ignores that — your notes stay clean.

5. **It builds your personal knowledge map.** Related ideas get connected together, so FKT knows the *shape* of what you know.

6. **It schedules the right moment to remind you.** Using a well-known memory science algorithm, FKT decides when each idea needs a quick refresher — then pops a tiny quiz during an idle moment.

That is it. The whole loop is designed so that **you only ever press one button**; everything else is automatic.

| What it watches | What it learns from it |
|---|---|
| Your screen (the active window only) | The words and ideas you are studying |
| Your microphone | Whether the environment is quiet or noisy |
| Your webcam *(optional)* | Whether you look focused or drowsy |
| Your typing rhythm | How deeply you are concentrating |

---

## Your privacy

Privacy is a core design choice, not an afterthought:

- **Nothing leaves your computer.** Everything runs locally. No account, no cloud, no uploads — FKT never sends data anywhere.
- **Sensitive info is removed automatically.** Credit card numbers, emails, passwords, and similar details are detected and scrubbed before anything is saved.
- **Private windows are skipped.** Windows with titles like "password", "login", or "bank" are never looked at.
- **You stay in control.** FKT only watches while a study session is active — flip the switch off and it goes fully quiet.
- **Your data is a file you own.** Everything is stored in a single database file on your machine. Delete it any time; nothing is hidden.

---

## What you will see

FKT shows you a simple dashboard in your browser:

- **Overview** — a quick snapshot of how your study is going.
- **Review** — the quick quizzes FKT generates for you, with an "Again / Hard / Good / Easy" rating, just like a flashcard app.
- **Knowledge base** — every idea FKT has captured, searchable in one place.
- **Add idea** — if you want, add your own items for FKT to track.

---

## Getting started

**For a non-technical try-out**, you will still need one step that involves the terminal, but that is the whole story:

```
python setup.py --run
```

That single command installs everything, then starts the program. Open your browser to **http://localhost:5000** and press **Start Studying**.

---

# For technical readers

Everything below assumes you are comfortable with Python, terminals, and reading code.

## Quick Start

### Prerequisites
- Python 3.11 or higher
- Node.js 18+ (for building the frontend)
- Windows 10/11 (primary supported platform; Linux/macOS require manual Tesseract install)

### One-Command Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/FKT.git
cd FKT

# Run the auto-setup (handles venv, deps, Tesseract, .env, DB)
python setup.py

# Start the full application
python setup.py --run
```

That's it. `setup.py` will:
1. Remove any duplicate virtual environments
2. Create a clean `venv/`
3. Install all dependencies
4. Auto-download and silently install Tesseract OCR (Windows only)
5. Create `.env` from the example if it doesn't exist
6. Initialise the SQLite database
7. *(with `--run`)* Start both the background tracker and the web dashboard

The dashboard will be at **http://localhost:5000**

### Manual Start (Advanced)

If you prefer to run it manually without the `setup.py` auto-launcher:

```bash
# Activate the virtual environment
.\venv\Scripts\activate          # Windows
source venv/bin/activate         # Linux/macOS

# Background tracker (asks about webcam on start)
python -m tracker_app.main

# In a second terminal: web dashboard -> http://localhost:5000
python -m tracker_app.web.app
```

(`python setup.py --run` starts both together.)

---

## How It Works (system view)

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

## Architecture

```
FKT/
├── setup.py                        # ← START HERE: auto-setup + launcher
├── .env.example                    # Environment template
├── requirements.txt                # Dependencies
│
└── tracker_app/
    ├── main.py                     # Background tracker entry point
    ├── config.py                   # Single source of truth for all settings
    │
    ├── tracking/                   # Sensing & signal processing
    │   ├── loop.py                 # Main tracking loop (5s cycles)
    │   ├── ocr_module.py           # Screen capture + Tesseract OCR
    │   ├── keyword_extractor.py    # YAKE! + spaCy NER keyword extraction
    │   ├── audio_module.py         # Mic recording + audio classification
    │   ├── webcam_module.py        # EAR attention (lazy-loaded MediaPipe)
    │   ├── cle_module.py           # Cognitive Load Estimator (novel)
    │   ├── intent_module.py        # RandomForest intent classifier
    │   ├── knowledge_graph.py      # NetworkX semantic concept graph
    │   ├── activity_monitor.py     # Session tracking + concept scheduling
    │   └── privacy_filter.py       # PII detection + redaction
    │
    ├── learning/                   # Memory science
    │   ├── sm2_memory_model.py     # SuperMemo-2 algorithm
    │   ├── memory_model.py         # Ebbinghaus forgetting curve + AWFC
    │   ├── concept_scheduler.py    # SM-2 scheduling for tracked concepts
    │   ├── learning_tracker.py     # Manual flashcard management
    │   └── text_quality_validator.py # OCR text quality filtering
    │
    ├── db/                         # Data persistence
    │   ├── models.py               # SQLAlchemy ORM models
    │   └── db_module.py            # DB initialisation
    │
    ├── web/                        # Dashboard
    │   ├── app.py                  # Flask + Socket.IO server
    │   ├── api.py                  # REST API endpoints
    │   ├── auth.py                 # API key authentication
    │   ├── realtime.py             # Socket.IO live updates
    │   └── frontend/               # React + TypeScript + Tailwind
    │       └── src/
    │           ├── pages/          # Overview, Review, KnowledgeBase, Add
    │           └── components/     # IntentFeedbackToast
    │
    ├── models/                     # Trained ML models
    │   └── intent_classifier.pkl   # RandomForest intent model (3 MB)
    │
    ├── training_data/              # ML training datasets
    │   └── intent_training_data.json  # 2,500 labelled synthetic samples
    │
    ├── scripts/                    # Utility scripts
    │   └── train_models_from_logs.py  # Retrain intent classifier
    │
    └── tools/                      # Dev utilities
        ├── populate.py             # Seed the database with test data
        ├── preflight_check.py      # Stress test the intent pipeline
        └── launcher.py             # Alternative CLI launcher
```

---

## Configuration

All settings are in `.env` (created automatically by `setup.py`). You can also override any setting by editing `tracker_app/config.py` directly.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me` | Flask session secret — **change before deploying** |
| `TRACK_INTERVAL` | `5` | Main loop interval (seconds) |
| `SCREENSHOT_INTERVAL` | `20` | How often to run OCR (seconds) |
| `AUDIO_INTERVAL` | `15` | How often to classify audio (seconds) |
| `WEBCAM_INTERVAL` | `45` | How often to check eye-tracking (seconds) |
| `ALLOW_WEBCAM` | `true` | Enable webcam by default (can be overridden at startup) |
| `SESSION_ALLOWED_INTENTS` | `studying` | Intent labels allowed to persist concepts inside an active session (e.g. `studying,passive`) |
| `TESSERACT_PATH` | *(auto-detected)* | Path to Tesseract executable |
| `DEBUG` | `True` | Flask debug mode |

---

## Retraining the Intent Model

The intent classifier is trained on synthetic data by default. To retrain (e.g., after collecting real feedback):

```bash
python -m tracker_app.scripts.train_models_from_logs
```

This will:
1. Load existing training data from `training_data/intent_training_data.json`
2. If no file exists, generate a fresh 2,500-sample synthetic dataset
3. Train a RandomForest with 5-fold cross-validation
4. Print accuracy, classification report, and feature importances
5. Save the model to `models/intent_classifier.pkl`

Restart the tracker to pick up the new model.

---

## Running Tests

```bash
# Activate venv first
.\venv\Scripts\activate

# Run the full test suite
python -m pytest tracker_app/tests/ -v

# Run a specific module
python -m pytest tracker_app/tests/test_sm2.py -v
```

---

## Troubleshooting

**App won't start / crashes immediately**
```bash
python setup.py          # re-run setup; it's idempotent
python -m tracker_app.config  # prints config summary and validates paths
```

**Tesseract not found**
```bash
python setup.py --skip-deps   # re-runs Tesseract check + install only
```
Or install manually from [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki) and add the path to `.env`:
```
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

**Dashboard shows blank / 500 error**
The React frontend needs to be built:
```bash
cd tracker_app/web/frontend
npm install
npm run build
```

**Intent model warnings**
```bash
python -m tracker_app.scripts.train_models_from_logs
```

**Database errors**
```bash
python -c "from tracker_app.db.db_module import init_all_databases; init_all_databases()"
```

**High CPU usage**
Increase intervals in `.env`:
```
SCREENSHOT_INTERVAL=40
AUDIO_INTERVAL=30
WEBCAM_INTERVAL=90
```

---

## Novel Contributions

FKT introduces several ideas not found in any existing knowledge management or spaced-repetition system:

**Cognitive Load Estimator (CLE)** — Estimates mental engagement from keystroke dynamics (inter-key interval entropy, typing speed variance, backspace rate, pause density, burst length) without requiring a camera. Based on Epp et al. (2011) and Vizer et al. (2009).

**Attention-Weighted Forgetting Curve (AWFC)** *(in development)* — Adjusts the Ebbinghaus decay constant λ based on your attention level at the moment a concept was first encountered. Concepts learned during high-focus sessions decay up to 30% slower.

**Cross-Session Concept Drift Detection** *(in development)* — Tracks how your understanding of each concept evolves across weeks using Jaccard distance on semantic co-occurrence. Surfaces stagnant or regressing concepts before they fully decay.

**Knowledge Gap Mapping** *(in development)* — Uses graph traversal to identify concepts that are adjacent to your existing knowledge but not yet in your graph, enabling proactive learning path suggestions.

**Micro-Quiz Interrupts** *(in development)* — Automatically generates contextual quiz questions from your own captured content during idle periods, feeding results back into SM-2 scheduling.

---

## Roadmap

| Phase | Status | Description |
|---|---|---|
| 1 — Crash Fixes | ✅ Done | All 5 critical crashes resolved; config unified; CLE built |
| 2 — ML Pipeline | ✅ Done | YAKE! extractor; RandomForest intent classifier; training script |
| 3 — Database | ✅ Done | SQLite + SQLAlchemy; custom migration runner; FK relationships |
| 4 — AWFC | ✅ Done | Personalised forgetting curve (attention-weighted λ) |
| 5 — Audio | ✅ Done | MFCC-based audio classifier; async recording |
| 6 — Graph | ✅ Done | Concept graph; drift detection; graph page |
| 7 — Micro-Quiz | ✅ Done | Idle-triggered quiz interrupts; quiz page |
| 8 — Performance | ✅ Done | Thread pool; lazy-loaded pipelines; adaptive throttling |
| 9 — Self-Improving | ✅ Done | Auto-retrain from session logs |
| 10 — Browser Ext | ✅ Done | `/ingest` endpoint + FKT Capture Chrome extension |
| 11 — Frontend | ✅ Done | React dashboard: overview, graph, quiz, review, add concept |

See [`MAKEOVER_PLAN.md`](MAKEOVER_PLAN.md) for the build-out status, and `architecture/` for the ADRs and design docs.

---

## Academic Background

FKT was developed as a final-year B.E. project in Computer Science (AI/ML) at Bharat College of Engineering, Mumbai (2024–25). The system integrates:

- **Ebbinghaus forgetting curve** (1885) — mathematical model of memory decay
- **SuperMemo-2 algorithm** (Wozniak, 1987) — research-validated spaced repetition
- **YAKE!** (Campos et al., 2020) — unsupervised single-document keyword extraction
- **Keystroke dynamics** (Epp et al., 2011; Vizer et al., 2009) — cognitive load from typing patterns
- **MediaPipe FaceMesh** — real-time facial landmark detection for EAR computation

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes, add tests
4. Run the test suite: `python -m pytest tracker_app/tests/`
5. Submit a pull request

Please read [`MAKEOVER_PLAN.md`](MAKEOVER_PLAN.md) and `architecture/adr/` before contributing to understand what is built and planned and avoid duplicate work.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built for the ambitious learner.**
*Session-gated capture. Scientific scheduling. Zero manual effort.*

</div>