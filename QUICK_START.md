# 🚀 Forgotten Knowledge Tracker - Quick Start Guide

## ✅ Current Status
Your FKT application is now **fully configured and running**!

- ✅ All dependencies installed
- ✅ Database paths unified
- ✅ Web dashboard running at **http://localhost:5000**
- ✅ Template syntax errors fixed
- ✅ MediaPipe webcam tracking ready

---

## 📋 What's Running Right Now

You currently have the **Web Dashboard** running. Check these terminal windows:

1. **Terminal 1**: Web Dashboard (Flask) - Port 5000
2. **Terminal 2**: (Available for automated tracker)

---

## 🎯 Quick Actions

### 1️⃣ View the Dashboard
Open your browser and go to:
```
http://localhost:5000
```

You'll see:
- 📊 **Stats Dashboard**: Due items, active items, success rate
- 📚 **Recent Items**: Your latest flashcards
- 🔍 **Context Scanner**: Discovered concepts (empty until tracker runs)

---

### 2️⃣ Add Your First Flashcard

**Option A: Manual Entry**
1. Click **"Add New Item"** button (or go to `/add`)
2. Fill in:
   - **Question**: "What is spaced repetition?"
   - **Answer**: "A learning technique that increases intervals of time between reviews"
   - **Tags**: "learning, memory"
3. Click **"Add Item"**

**Option B: From Discovered Concepts** (after running tracker)
1. Run the automated tracker (see step 3)
2. Wait for concepts to appear in "Recently Discovered"
3. Click the **"+"** button next to any concept
4. Form pre-fills automatically!

---

### 3️⃣ Start the Automated Tracker

Open a **new terminal** and run:

```powershell
cd C:\Users\hp\Desktop\FKT
py311 tracker_app/main.py
```

**What it does:**
- 🖥️ Scans your screen every 20 seconds (OCR)
- 🎤 Records audio every 15 seconds (optional)
- 👁️ Tracks attention via webcam (optional - you'll be prompted)
- 🧠 Discovers concepts and stores them in `tracking_concepts.db`

**First-time setup:**
- You'll be asked: "Enable webcam tracking? (y/n)"
- Type `y` for yes or `n` for no

---

### 4️⃣ Review Your Flashcards

1. Go to **http://localhost:5000**
2. See "Items Due Now" count
3. Click **"Start Review Session"**
4. Rate each card:
   - **Again** (0-1): Didn't remember
   - **Hard** (2): Struggled to remember
   - **Good** (3-4): Remembered correctly
   - **Easy** (5): Instant recall

The SM-2 algorithm adjusts intervals based on your ratings!

---

## 🔧 Using the Correct Python Version

**Important**: You must use **Python 3.11** (not 3.13) because that's where all packages are installed.

### Commands Reference:

| Task | Command |
|------|---------|
| Run Dashboard | `py311 tracker_app/web_dashboard.py` |
| Run Tracker | `py311 tracker_app/main.py` |
| Check Config | `py311 tracker_app/config.py` |
| Install Packages | `py311 -m pip install <package>` |

---

## 📁 Data Storage

All data is stored in `tracker_app/data/`:

```
tracker_app/data/
├── learning_tracker.db       # Your flashcards (SM-2 data)
├── tracking_concepts.db       # Discovered concepts (from tracker)
├── intent_validation.db       # Intent prediction logs
├── tracking_analytics.db      # Usage analytics
└── sessions.db                # Activity sessions
```

---

## 🎨 Dashboard Features

### Home Page (/)
- **Stats Cards**: Overview of your learning progress
- **Recent Items**: Latest flashcards you added
- **Context Scanner**: Shows real-time tracker status + discovered concepts

### Add Page (/add)
- **Manual Entry**: Create flashcards from scratch
- **URL Pre-fill**: Supports `?question=...&tags=...` parameters
- **Difficulty Levels**: Easy, Medium, Hard
- **Types**: Concept, Definition, Code, Fact

### Review Page (/review)
- **SM-2 Algorithm**: Optimal spacing intervals
- **Quality Ratings**: 0-5 scale
- **Progress Tracking**: Shows current position in review queue

---

## 🧪 Testing the Integration

### Full Workflow Test:

1. **Open Dashboard** → http://localhost:5000
2. **Start Tracker** → `py311 tracker_app/main.py` (new terminal)
3. **Browse Learning Content** → Open Wikipedia, read a Python tutorial, etc.
4. **Wait 1-2 minutes** → Tracker scans and discovers concepts
5. **Refresh Dashboard** → See concepts in "Recently Discovered"
6. **Click "+"** → Create flashcard instantly
7. **Review** → Go to `/review` and test SM-2 scheduling

---

## ❓ Troubleshooting

### Dashboard won't load
```powershell
# Check if Flask is running
# You should see: "Running on http://127.0.0.1:5000"
```

### "No module named 'flask'"
```powershell
# Use py311, not python
py311 tracker_app/web_dashboard.py
```

### Tracker crashes on start
```powershell
# Check config validation
py311 tracker_app/config.py

# Common issues:
# - Tesseract not installed (OCR will be disabled)
# - Model files missing (intent/audio will use fallback)
```

### No concepts appearing
- Make sure tracker is actually running
- Check `tracker_app/data/tracking_concepts.db` exists
- Run for at least 2-3 minutes on content-rich pages

---

## 🚦 Stopping the Application

### Stop Dashboard:
In the terminal running Flask, press: **Ctrl + C**

### Stop Tracker:
In the terminal running tracker, press: **Ctrl + C**

---

## 📊 What Success Looks Like

After 10-15 minutes of running both systems:

✅ Dashboard shows 5+ discovered concepts  
✅ You've created 2-3 flashcards  
✅ Database files exist in `tracker_app/data/`  
✅ Stats show "Active Items: 2-3"  
✅ Review session works smoothly  

---

## 🎯 Next Steps

1. **Immediate**: Open http://localhost:5000 in your browser
2. **5 minutes**: Add 3 sample flashcards manually
3. **Optional**: Start the automated tracker
4. **Tomorrow**: Come back and review your flashcards (SM-2 in action!)

---

## 💡 Pro Tips

- **Tag Everything**: Use tags like "python", "ml", "work" for better organization
- **Be Specific**: Good questions are specific and testable
- **Regular Reviews**: The SM-2 algorithm works best with consistent reviews
- **Trust the System**: Don't manually adjust intervals - let SM-2 optimize them

---

**Need Help?** Check `walkthrough.md` for the complete technical documentation.

**Happy Learning! 🧠✨**
