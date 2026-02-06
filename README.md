# 🧠 Forgotten Knowledge Tracker (FKT)

> **A "Second Brain" that manages itself.**  
> *Automated knowledge discovery paired with scientific spaced repetition.*

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## ⚡ Quick Start

### 1. Run the Dashboard
Access your premium learning interface:
```bash
python -m tracker_app.web.app
```
👉 **Open**: http://localhost:5000

### 2. Run the Tracker
Start the background discovery engine in a **new terminal**:
```bash
python -m tracker_app.main
```

---

## 📖 Overview

FKT is a hybrid learning system that solves the "collecting but forgetting" problem. It combines **automated context awareness** (tracking what you read/watch) with **active recall** (SM-2 spaced repetition).

### ✨ Key Features
- **🤖 Context Scanner**: Uses OCR and Intent Recognition to auto-discover concepts from your screen.
- **🎤 Multi-Modal Input**: Captures audio and webcam attention metrics to gauge learning intensity.
- **🧠 Automated Knowledge Graph**: Builds a network of related concepts without manual data entry.
- **📊 Premium Web Dashboard**: A Flask-based UI to review flashcards, visualize progress, and manage your knowledge base.
- **📅 Scientific Scheduling**: Built-in SuperMemo-2 (SM-2) algorithm ensures you review items at the optimal time.

---

## 🛠️ Project Structure

The project follows a modern, modular Python package structure:

```
FKT/
├── tracker_app/
│   ├── core/              # Brain: OCR, NLP, SM-2, Metrics
│   ├── web/               # UI: Flask Dashboard & API
│   ├── models/            # AI: Pre-trained classifiers
│   ├── scripts/           # Utils: Training & Maintenance
│   ├── tests/             # Quality Assurance
│   └── data/              # Storage: Local SQLite Databases
├── setup.py               # Package Configuration
├── requirements.txt       # Dependencies
└── README.md              # Documentation
```

---

## 🚀 Detailed Usage

### 1. Dashboard (`tracker_app.web.app`)
The command center for your knowledge.
- **Home**: View stats and recently discovered concepts.
- **Add**: Create flashcards (manual or auto-filled from discovery).
- **Review**: Active recall session with SM-2 grading (0-5 scale).

### 2. Tracker (`tracker_app.main`)
The background agent.
- **OCR**: Scans screen text every 20s.
- **NLP**: Extracts keywords using KeyBERT/spaCy.
- **Intent**: Classifies activity (Studying vs Passive).
- **Audio**: Detects speech/music environment.

### 3. Model Retraining (`tracker_app.scripts.train_models`)
If you encounter model version warnings:
```bash
python -m tracker_app.scripts.train_models
```

---

## 🧪 Testing

Run the full test suite to ensure system integrity:
```bash
python -m unittest discover tracker_app/tests
```
*(Requires Python 3.11)*

---

## 🔧 Configuration

All settings are managed in `tracker_app/config.py`.
- **Database Paths**: Auto-configured in `tracker_app/data/`
- **Tesseract Path**: Set via `TESSERACT_PATH`
- **Intervals**: Adjustable tracking frequency

---

**Built for the ambitious learner.**
