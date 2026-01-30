# 🚀 Enhanced Tracker - Quick Start (30 seconds)

## What You Have Now

You have **two powerful systems**:

1. **Learning Tracker** (`launcher.py cli`) - Explicit learning with SM-2 spaced repetition
2. **Enhanced Activity Tracker** (NEW!) - Passive monitoring that discovers & schedules concepts

## Quick Start - 3 Steps

### Step 1: Start the Dashboard

```bash
cd c:\Users\hp\Desktop\FKT\tracker_app
python tracker_dashboard.py
```

You'll see:
```
* Running on http://127.0.0.1:5001
```

### Step 2: Open Dashboard in Browser

Go to: **http://localhost:5001**

You'll see:
- 🟢 Status: "Not Tracking"
- **▶ Start Tracking** button
- Real-time stats cards
- Analytics section

### Step 3: Start Tracking Activity

1. Click **▶ Start Tracking** button
2. Do your work (watch tutorials, code, read, etc.)
3. Dashboard updates in real-time:
   - Session duration
   - Concepts encountered (from screen text)
   - Attention/focus score
   - Top concepts to review
4. Click **⏹ Stop Tracking** when done
5. Dashboard saves all analytics
6. Click **📥 Export Data** to download JSON

## What Gets Tracked

**While you work, the system automatically:**

✅ Monitors active window (what app you're using)  
✅ Analyzes keyboard/mouse activity (interaction rate)  
✅ Scans screen text (OCR) to extract concepts  
✅ Analyzes audio (detects speech/music/silence)  
✅ Tracks attention from webcam (focus level)  
✅ Predicts your intent (studying, working, browsing, etc.)  

**Then automatically:**
- Schedules concepts for review using SM-2 algorithm
- Tracks intent prediction accuracy
- Generates daily/weekly analytics
- Stores everything locally

## Example Dashboard Flow

```
Before Session:
├─ Status: 🔴 Not Tracking
├─ Quick Stats: All "--"
└─ Top Concepts: "No concepts due"

After clicking ▶ Start:
├─ Status: 🟢 Tracking Active
├─ [You browse Python tutorial for 30 mins]
├─ Dashboard updates every 2 seconds:
│  ├─ Duration: 30 min
│  ├─ Concepts: 15 unique concepts found
│  ├─ Attention: 0.82 (82% focused)
│  └─ Top Concepts:
│     ├─ "Python" (encountered 8 times, relevance 92%)
│     ├─ "List" (encountered 5 times, relevance 78%)
│     └─ "Function" (encountered 4 times, relevance 72%)

After clicking ⏹ Stop:
├─ Status: 🔴 Not Tracking
├─ Analytics Saved
├─ Intent Accuracy: 75%
├─ Daily Concepts: 15
└─ Export ready to download
```

## Dashboard Sections Explained

### 📊 Session Cards (Top)
Real-time updates while tracking:
- **Session Duration** - How long tracking (minutes)
- **Concepts Encountered** - Unique concepts found on screen
- **Avg Attention** - Average focus score (0-1)

### 📚 Top Concepts to Review
Shows concepts due for review, sorted by SM-2 algorithm:
- **Python** - Encountered 8 times, relevance 92%
- Each shows relevance score (how important based on exposure)
- Click to see full encounter history

### 📈 Analytics Cards
Historical stats:
- **Intent Accuracy** - How well system guesses what you're doing (improves with time)
- **Daily Concepts** - Unique concepts encountered today
- **This Week** - Total minutes tracked this week
- **Avg Attention** - Average focus score for the week

## Features Explained

### 🎯 SM-2 Scheduling
Concepts are automatically scheduled for review:
- New concept → Review in 1 day
- If you see it frequently → Review sooner
- If you understand it → Review later
- Gets smarter the more you use it

### 📝 Intent Prediction
System learns what you're doing:
- "You're studying Python" (confidence 85%)
- Over time, learns which contexts = studying vs. working
- Accuracy improves as you provide feedback

### 📊 Analytics
Tracks your learning patterns:
- How much time you spend learning
- What concepts you encounter most
- Focus patterns throughout the day/week
- Intent prediction accuracy

## Data Location

All data stored locally (no cloud):
- `data/tracking_concepts.db` - Concepts with SM-2 intervals
- `data/intent_validation.db` - Intent predictions + accuracy
- `data/tracking_analytics.db` - Session data

Export as JSON for analysis.

## Common Tasks

### "I want to review the concepts I found"
1. Click **⏹ Stop Tracking**
2. Look at **📚 Top Concepts to Review**
3. Each shows encounter count and relevance
4. Add important ones to Learning Tracker for spaced repetition

### "I want to see my progress"
1. Check **📈 Analytics Cards**
2. See concepts encountered today/this week
3. See focus patterns (avg attention)
4. See intent prediction accuracy improving

### "I want to save my tracking session"
1. Click **📥 Export Data**
2. JSON file downloaded with all session data
3. Includes: concepts, duration, attention, analytics
4. Can backup or analyze separately

### "I want to integrate with Learning Tracker"
1. Track something in Enhanced Tracker
2. Find concepts you want to learn deeply
3. Add them to Learning Tracker (`python launcher.py cli`)
4. Both systems use SM-2 for optimal spacing

## Troubleshooting

**"Dashboard won't start"**
- Make sure port 5001 is free
- Try: `python tracker_dashboard.py --port 5002`

**"Status shows 'Not Tracking' after clicking Start"**
- Make sure modules loaded (audio, webcam, etc.)
- Check browser console for errors (F12)
- Refresh page (Ctrl+R)

**"No concepts showing up"**
- Make sure you have text on screen (not blank)
- Tracking needs 30+ seconds to extract concepts
- Check OCR module is working

**"Export button doesn't work"**
- Make sure tracking has run at least once
- Check browser downloads folder
- Try Ctrl+Shift+Delete to clear cache

## Next Steps

1. ✅ Start dashboard: `python tracker_dashboard.py`
2. ✅ Open browser: `http://localhost:5001`
3. ✅ Click **▶ Start Tracking**
4. ✅ Use your computer normally for 30+ minutes
5. ✅ Click **⏹ Stop Tracking**
6. ✅ Check "Top Concepts to Review"
7. ✅ Click **📥 Export Data** to save session

## System Requirements

- Python 3.8+ ✅
- Flask ✅ (already installed)
- SQLite ✅ (built-in)
- Local storage for data ✅
- No internet required ✅

## Files Reference

| File | Purpose |
|------|---------|
| `tracker_dashboard.py` | Web server (Flask) |
| `core/tracker_enhanced.py` | Core tracking engine |
| `templates/tracker_dashboard.html` | Dashboard UI |
| `test_tracker_enhanced.py` | Tests (all passing ✅) |
| `TRACKER_ENHANCED_README.md` | Full documentation |

---

**You're all set!** Start the dashboard and begin tracking.  
Questions? Check TRACKER_ENHANCED_README.md for full documentation.

✨ **Happy tracking!** ✨
