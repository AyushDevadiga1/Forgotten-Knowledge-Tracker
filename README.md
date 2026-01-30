# 🧠 Forgotten Knowledge Tracker (FKT)

> **AI-Powered Spaced Repetition Learning System**

A holistic learning tracker that combines automated knowledge discovery with scientifically-validated spaced repetition (SM-2 algorithm). Track what you learn, review optimally, and never forget again.

---

## ✨ Features

### 🤖 Automated Knowledge Discovery
- **Screen OCR**: Extracts concepts from your screen automatically
- **Audio Analysis**: Identifies learning contexts from ambient audio
- **Attention Tracking**: Uses webcam + MediaPipe for focus detection
- **Concept Mapping**: Builds a knowledge graph of discovered topics

### 📚 User-Controlled Learning
- **SM-2 Algorithm**: Science-backed spaced repetition scheduling
- **Flashcard System**: Create and review items with optimal intervals
- **Quality Ratings**: 0-5 scale adapts to your performance
- **Premium Dashboard**: Modern, responsive UI built with Tailwind CSS

### 🔗 Seamless Integration
- **One-Click Conversion**: Discovered concepts → Flashcards instantly
- **Unified Storage**: All data in one organized location
- **Real-Time Sync**: Dashboard updates as tracker discovers concepts

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ (3.11 recommended)
- Windows OS
- Tesseract OCR (optional, for screen text extraction)

### Installation

1. **Clone/Download** this repository

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

3. **Run the Dashboard**:
   ```bash
   python tracker_app/web_dashboard.py
   ```
   Open http://localhost:5000

4. **Optional - Run Automated Tracker**:
   ```bash
   python tracker_app/main.py
   ```

📖 **See [QUICK_START.md](QUICK_START.md) for detailed instructions.**

---

## 📁 Project Structure

```
FKT/
├── tracker_app/
│   ├── main.py                 # Automated tracker entry point
│   ├── web_dashboard.py        # Flask web interface
│   ├── config.py               # Centralized configuration
│   ├── core/
│   │   ├── tracker.py          # Enhanced activity tracker
│   │   ├── learning_tracker.py # SM-2 flashcard manager
│   │   ├── sm2_memory_model.py # SuperMemo-2 algorithm
│   │   ├── ocr_module.py       # Screen text extraction
│   │   ├── webcam_module.py    # MediaPipe attention tracking
│   │   ├── audio_module.py     # Audio classification
│   │   └── intent_module.py    # Intent prediction
│   ├── templates/              # Jinja2 HTML templates
│   └── data/                   # SQLite databases (auto-created)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── QUICK_START.md              # Step-by-step guide
└── walkthrough.md              # Technical documentation
```

---

## 🎯 How It Works

### Automated Discovery Flow
```
Screen Activity → OCR → Keyword Extraction → Concept Discovery
                                          ↓
                                   Knowledge Graph
                                          ↓
                            "Recently Discovered" on Dashboard
```

### User Learning Flow
```
Concept Discovery → Click "+" → Fill Answer → Add Flashcard
                                                   ↓
                                              SM-2 Scheduler
                                                   ↓
                                           Optimal Review Times
```

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11, Flask |
| Database | SQLite3 |
| ML/NLP | spaCy, KeyBERT, SentenceTransformers |
| Computer Vision | OpenCV, MediaPipe |
| Audio | librosa, sounddevice |
| Frontend | Tailwind CSS, Lucide Icons |
| Algorithm | SM-2 (SuperMemo-2) |

---

## 📊 Screenshots

### Dashboard
- Stats overview (Due, Active, Mastered items)
- Recently added flashcards
- **Context Scanner** with discovered concepts

### Review Session
- Card-by-card review interface
- Quality rating (0-5 scale)
- SM-2 interval calculation

### Add Flashcard
- Manual entry form
- Pre-fill from discovered concepts
- Tags and difficulty levels

---

## 🧪 Usage Examples

### Create a Flashcard Manually
```python
# Via Dashboard: http://localhost:5000/add
Question: "What is the time complexity of binary search?"
Answer: "O(log n) - divides search space in half each iteration"
Tags: "algorithms, computer-science"
Difficulty: Medium
```

### Review Due Items
```python
# Via Dashboard: http://localhost:5000/review
1. Review each card
2. Rate quality (0-5)
3. SM-2 calculates next review date
4. Repeat until queue is empty
```

---

## 📈 SM-2 Algorithm

The SuperMemo-2 algorithm optimizes review intervals based on:

- **Quality Rating**: How well you remembered (0-5)
- **Ease Factor**: Adjusted based on performance
- **Interval**: Days until next review

**Example**:
- Rate "Easy" (5) → Next review in 10 days
- Rate "Hard" (2) → Next review in 1 day
- Automatic adjustment for long-term retention

---

## 🔒 Privacy & Data

- **100% Local**: All data stored locally in SQLite
- **No Cloud Sync**: Nothing leaves your machine
- **Optional Components**: Disable webcam/audio if preferred
- **Transparent Storage**: Plain SQLite databases you can inspect

---

## 🐛 Known Limitations

- **Single User**: No multi-user support
- **Windows Only**: Currently optimized for Windows
- **Tesseract Required**: For OCR features
- **Model Files**: Some ML features need pre-trained models

---

## 🤝 Contributing

This is a personal learning project, but suggestions are welcome!

---

## 📝 License

This project is for educational purposes. Use at your own risk.

---

## 🙏 Acknowledgments

- **SM-2 Algorithm**: Developed by Piotr Woźniak (SuperMemo)
- **MediaPipe**: Google's ML solutions for face tracking
- **Flask**: Lightweight web framework
- **Tailwind CSS**: Utility-first CSS framework

---

## 📞 Support

- See [QUICK_START.md](QUICK_START.md) for setup help
- Check [walkthrough.md](walkthrough.md) for technical details
- Run `python tracker_app/config.py` to validate your setup

---

**Built with ❤️ for better learning**
