<div align="center">

# 🧠 Forgotten Knowledge Tracker (FKT)

**A passive AI second-brain that watches what you study, builds a knowledge graph from it, and reminds you before you forget.**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Active Development](https://img.shields.io/badge/status-active%20development-green.svg)]()
[![Platform: Windows](https://img.shields.io/badge/platform-Windows%20(primary)-lightgrey.svg)]()

*No manual note-taking. No manual flashcard creation. Just study — FKT handles the rest.*

</div>

---

## What Is FKT?

FKT is a desktop application that runs silently in the background while you work or study. It uses your screen (OCR), microphone (audio environment detection), webcam (optional eye-tracking), and keyboard/mouse activity (Cognitive Load Estimation) to understand **what you are learning and how focused you are**. From this it builds a personal knowledge graph, calculates how likely you are to forget each concept, and schedules intelligent review sessions at exactly the right moment.

Think of it as a spaced-repetition system (like Anki) — but one that fills itself automatically from your existing screen activity, rather than requiring you to manually create cards.

---

## Key Features

### Passive Knowledge Capture
- **Screen OCR** — captures keywords from whatever is on your screen every 20 seconds using Tesseract OCR (auto-installed on first run)
- **Active Window Detection** — only scans the foreground window, not your entire screen
- **Privacy Filter** — automatically redacts emails, passwords, credit card numbers, and other sensitive data before anything is stored
- **Browser Extension** *(coming Phase 10)* — send tab text directly to FKT without OCR, as the primary alternative to screen capture

### Attention Tracking
- **Webcam Eye-Tracking** (optional, strongly recommended) — MediaPipe FaceMesh measures Eye Aspect Ratio (EAR) to detect focus vs. drowsiness
- **Cognitive Load Estimator (CLE)** — a novel keystroke-dynamics system that estimates your mental engagement from typing rhythm, backspace rate, pause patterns, and burst length — works with or without a webcam
- **Blended Attention Score** — when both are active, webcam provides 70% of the signal and CLE provides 30%

### Knowledge Graph
- **Automatic concept extraction** — YAKE! + spaCy NER extracts and ranks meaningful keywords from screen text
- **Semantic edge linking** — concepts that frequently co-occur or are semantically similar are connected in the graph
- **Concept Drift Detection** *(coming Phase 6)* — tracks whether your understanding of a topic is evolving, stagnating, or decaying
- **Knowledge Gap Map** *(coming Phase 6)* — surfaces concepts you probably don't know but should, based on your graph's neighbourhood

### Memory Scheduling
- **SuperMemo-2 (SM-2) algorithm** — the same research-validated algorithm behind Anki and many language-learning apps
- **Attention-Weighted Forgetting Curve (AWFC)** *(coming Phase 4)* — concepts learned during high-focus sessions decay up to 30% slower than those absorbed passively
- **Micro-Quiz Interrupts** *(coming Phase 7)* — during idle periods, FKT pops a quick quiz using your own captured content, results feed directly into SM-2

### Intent Classification
- **Trained RandomForest classifier** — 96% cross-validated accuracy on 6 multi-modal features
- **3 activity states** — `studying`, `passive`, `idle`
- **Self-improving** *(coming Phase 9)* — retrains from your feedback every 50 corrections
- **Rule-based fallback** — if the model file is missing, heuristic rules ensure the system still works

### Dashboard
- **React + TypeScript frontend** — clean, minimal dark-mode interface
- **Overview page** — KPI cards, system status, recent items, performance chart
- **Review page** — full SM-2 flashcard review with quality rating (Again / Hard / Good / Easy)
- **Knowledge base** — searchable table of all tracked concepts and learning items
- **Add concept** — manually add flashcards with difficulty, type, and tags

---

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

If you prefer to run components separately:

```bash
# Activate the virtual environment
.\venv\Scripts\activate          # Windows
source venv/bin/activate         # Linux/macOS

# Terminal 1 — Background tracker
python -m tracker_app.main

# Terminal 2 — Web dashboard
python -m tracker_app.web.app
```

---

## How It Works

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

Every 5 seconds, FKT's tracking loop runs one cycle. OCR runs every 20 s, audio every 15 s, webcam every 45 s. All pipelines are lazy-loaded and run asynchronously so the loop never blocks.

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
| `TESSERACT_PATH` | *(auto-detected)* | Path to Tesseract executable |
| `DEBUG` | `True` | Flask debug mode |

---

## Privacy

FKT is designed to be fully local and private:

- **No cloud** — everything runs on your machine. No data is ever sent to any external server.
- **PII redaction** — the privacy filter automatically detects and redacts credit card numbers, email addresses, phone numbers, passwords, IP addresses, and API keys before any text is stored.
- **Sensitive windows** — windows with titles containing "password", "login", "bank", "private", "incognito" are automatically skipped.
- **Browser extension** *(coming)* — only activates on user-approved domains and only talks to `localhost`.
- **Local database** — all data is stored in a single SQLite file at `tracker_app/data/sessions.db`. You can delete it at any time.

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
| 2 — ML Pipeline | ✅ Done | YAKE! extractor; trained intent classifier; training script |
| 3 — Database | 🔲 Next | DateTime columns; Alembic migrations; FK relationships |
| 4 — AWFC | 🔲 Planned | Personalised forgetting curve |
| 5 — Audio | 🔲 Planned | MFCC-based audio classifier; async recording |
| 6 — Graph | 🔲 Planned | Concept drift; knowledge gap map |
| 7 — Micro-Quiz | 🔲 Planned | Idle-triggered quiz interrupts |
| 8 — Performance | 🔲 Planned | Thread pool; SSIM dedup; adaptive throttling |
| 9 — Self-Improving | 🔲 Planned | Auto-retrain from user feedback |
| 10 — Browser Ext | 🔲 Planned | Chrome extension as OCR alternative |
| 11 — Frontend | 🔲 Planned | Graph page; attention heatmap; weekly report |

See `FKT_IMPLEMENTATION_PLAN.md` for the full detailed plan with code samples for every phase.

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

Please read `FKT_IMPLEMENTATION_PLAN.md` before contributing to understand what is planned and avoid duplicate work.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built for the ambitious learner.**
*Passive capture. Scientific scheduling. Zero manual effort.*

</div>
