# 🚀 Forgotten Knowledge Tracker - Quick Start Guide

## ✅ Current Status
Your FKT application is now **professionally reorganized and portfolio-ready**!

- ✅ Modular package structure (`tracker_app/core`, `tracker_app/web`, etc.)
- ✅ Clean root directory (< 10 files)
- ✅ Unified database storage in `tracker_app/data/`
- ✅ Centralized ML models in `tracker_app/models/`
- ✅ Package-level absolute imports for production stability

---

## 🎯 Quick Actions

### 1️⃣ Run the Web Dashboard
Access your premium learning interface:

```bash
# From the project root (FKT/)
python -m tracker_app.web.app
```
👉 Open browser: **http://localhost:5000**

---

### 2️⃣ Run the Automated Tracker
In a **new terminal**, start the background discovery engine:

```bash
# From the project root (FKT/)
python -m tracker_app.main
```

---

### 3️⃣ Add Your First Flashcard
1. Open the dashboard at http://localhost:5000
2. Click **"Add New Item"**
3. Create a card with tags like `python`, `learning`, `memory`
4. The SM-2 algorithm will automatically schedule your first review!

---

## 🔧 Pro Tips for Interview Showcase

### Clean Structure
Point out the modular design to interviewers:
- **`core/`**: Business logic, OCR, and AI modules
- **`web/`**: Premium Flask-based frontend
- **`models/`**: Centralized ML model storage
- **`scripts/`**: One-off utilities (training, population, checks)
- **`data/`**: Git-ignored runtime data

### Commands Reference
| Task | Professional Command |
|------|----------------------|
| Run Dashboard | `python -m tracker_app.web.app` |
| Run Tracker | `python -m tracker_app.main` |
| Run Tests | `pytest tracker_app/tests/` |
| Train Models | `python -m tracker_app.scripts.train_models` |
| Preflight Check | `python -m tracker_app.scripts.preflight_check` |

---

## 📁 Directory Overview

```
FKT/
├── README.md              # High-level overview
├── QUICK_START.md         # This guide
├── setup.py               # Package configuration
├── LICENSE                # MIT License
├── tracker_app/           # Main package
│   ├── core/              # Business logic
│   ├── web/               # Flask UI
│   ├── models/            # ML models
│   ├── scripts/           # Utilities
│   └── data/              # SQLite DBs (auto-created)
└── requirements.txt       # Dependencies
```

---

## ❓ Troubleshooting

### Import Errors
Always run commands using the `-m` flag from the root `FKT/` directory. This ensures the `tracker_app` package is correctly in your Python path.

### "No module named 'flask'"
Ensure you are using your environment where requirements are installed:
`python -m pip install -r requirements.txt`

---

**Built with ❤️ for better learning**
