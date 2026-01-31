# 🧠 Forgotten Knowledge Tracker (FKT)

**AI-powered spaced repetition learning system with automated knowledge discovery**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview

FKT combines automated knowledge discovery with scientifically-validated spaced repetition (SM-2 algorithm) to help you learn and retain information effortlessly.

### Key Features

- ✅ **SM-2 Spaced Repetition** - Science-backed optimal review intervals
- 🤖 **Automated Discovery** - Extracts concepts from screen, audio, attention state
- 📊 **Premium Dashboard** - Modern web interface built with Tailwind CSS
- 🔗 **Seamless Integration** - One-click conversion: discovered concepts → flashcards
- 📈 **Knowledge Graph** - Visualize connections between concepts

---

## Quick Start

### Prerequisites
- Python 3.11+
- (Optional) Tesseract OCR for screen text extraction

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/FKT.git
cd FKT

# 2. Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 3. Run the web dashboard
python -m tracker_app.web.app
# Open http://localhost:5000

# 4. (Optional) Run automated tracker
python -m tracker_app.main
```

📖 **See [QUICK_START.md](QUICK_START.md) for detailed setup instructions.**

---

## Architecture

```
┌─────────────────┐
│  Screen (OCR)   │────┐
│ Audio Analysis │────┤
│ Webcam Tracking│────┤
└─────────────────┘    │
                       ▼
                ┌──────────────┐
                │   Tracker    │
                │ (Discovers   │
                │  Concepts)   │
                └──────┬───────┘
                       │
                       ▼
              ┌────────────────┐
              │ Knowledge Graph│
              └────────┬───────┘
                       │
                       ▼
            ┌──────────────────────┐
            │   Web Dashboard      │
            │ - View concepts      │
            │ - Create flashcards  │
            │ - SM-2 reviews       │
            └──────────────────────┘
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.11, Flask, SQLite |
| **ML/NLP** | spaCy, KeyBERT, SentenceTransformers |
| **Computer Vision** | OpenCV, MediaPipe (attention tracking) |
| **Audio** | librosa, sounddevice |
| **Frontend** | Tailwind CSS, Lucide Icons |
| **Algorithm** | SM-2 (SuperMemo-2) |

---

## Project Structure

```
FKT/
├── tracker_app/
│   ├── core/              # Business logic
│   ├── models/            # ML models (.pkl files)
│   ├── web/               # Flask dashboard
│   ├── scripts/           # Utility scripts
│   ├── data/              # Runtime data (SQLite DBs)
│   └── main.py            # Automated tracker entry point
├── requirements.txt
├── README.md
└── QUICK_START.md
```

---

## Usage Examples

### 1. Manual Flashcard Creation
```python
# Via web interface: http://localhost:5000/add
Question: "What is the time complexity of binary search?"
Answer: "O(log n)"
Tags: "algorithms, cs"
```

### 2. Automated Discovery
```bash
# Start tracker
python -m tracker_app.main

# Browse content (Wikipedia, tutorials, docs)
# → Tracker discovers concepts
# → Dashboard shows "Recently Discovered"
# → Click "+" to create flashcard
```

### 3. Spaced Repetition Review
```bash
# Go to http://localhost:5000/review
# Rate each card (0-5)
# → SM-2 calculates optimal next review date
```

---

## SM-2 Algorithm

The SuperMemo-2 algorithm optimizes review intervals based on recall quality:

- **Quality 0-1** (Again): Next review in 1 day
- **Quality 2** (Hard): Next review in 2-3 days  
- **Quality 3-4** (Good): Next review in 5-10 days
- **Quality 5** (Easy): Next review in 10+ days

Intervals automatically adjust for long-term retention.

---

## Configuration

Key settings in [`tracker_app/config.py`](tracker_app/config.py):

```python
TRACK_INTERVAL = 5          # Tracking cycle (seconds)
SCREENSHOT_INTERVAL = 20     # OCR frequency
AUDIO_INTERVAL = 15          # Audio analysis frequency
WEBCAM_INTERVAL = 45         # Attention check frequency
```

---

## Privacy & Data

- **100% Local** - All data stored in local SQLite databases
- **No Cloud Sync** - Nothing leaves your machine
- **Optional Components** - Disable webcam/audio if preferred
- **Transparent** - Inspect databases anytime

---

## Development

### Running Tests
```bash
pytest tracker_app/tests/
```

### Retraining Models
```bash
python tracker_app/scripts/train_models.py
```

### Contributing
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## Known Limitations

- Single-user only (no authentication)
- Windows-optimized (cross-platform support planned)
- Requires Tesseract for OCR features
- Some ML models need retraining for optimal accuracy

---

## Acknowledgments

- **SM-2 Algorithm** - Piotr Woźniak (SuperMemo)
- **MediaPipe** - Google's ML solutions
- **Flask** - Pallets Projects
- **Tailwind CSS** - Tailwind Labs

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

## Contact

**Project Link**: [https://github.com/yourusername/FKT](https://github.com/yourusername/FKT)

---

**Built with ❤️ for better learning**
