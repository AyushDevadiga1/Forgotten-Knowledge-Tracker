import sqlite3
import random
from datetime import datetime, timedelta
import itertools

DB_PATH = r"C:\Users\hp\Desktop\FKT\tracker_app\tracking.db"

# -----------------------------
# Edge-case scenarios
# -----------------------------
eye_tracking = [
    "Eyes open and focused", "Eyes open but slightly distracted", "Normal blinking",
    "Small head movements", "Looking at intended target", "Eyes closed",
    "Extended eye closure", "Eyes partially covered", "Glasses glare",
    "Face partially out of frame", "Rapid or erratic eye movement", "Head turned away",
    "Low/bright lighting", "Camera malfunction", "False positives/negatives",
    "Intentional gaze shift", "Multitasking/divided attention", "Microexpressions",
    "Occlusion + poor lighting", "Abnormal blinking patterns", "Sudden head jerk",
    "Temporary occlusion"
]

audio_scenarios = [
    "Clear speech detected", "Soft background speech", "Speaking relevant content",
    "Normal tone and pace", "Intermittent silence", "No audio detected",
    "Extremely low volume", "Extremely high volume or shouting", "Muffled/distorted audio",
    "Overlapping speech", "Long silence", "Background noise too high",
    "Echo or feedback", "Microphone malfunction", "Speech not relevant to task",
    "Rapid speech or stammering", "Pauses mid-sentence", "Intentional whispers",
    "Background conversation partially audible", "Audio delayed or lagging",
    "Mixed emotions in tone", "Environmental disruptions"
]

ocr_scenarios = [
    "Keywords detected correctly", "Partial keywords detected", "High confidence OCR",
    "Dynamic content captured properly", "Multiple keywords in sequence",
    "No text detected", "Mislabeled/incorrect text detected", "Low-quality/blurry screen",
    "Obstructed screen", "Small font", "Screen glare/reflections", "Unusual font/color",
    "Dynamic content missed", "Partial screenshot", "Incorrect language/special chars",
    "Multiple windows overlapping", "Text partially occluded", "Fast-changing content",
    "Multiple languages/symbols", "Low contrast text", "Animated text/video overlays",
    "Mixed content (images + text)"
]

keyboard_mouse = [
    "Regular typing activity", "Frequent mouse clicks", "Mouse movement tracking",
    "Short pauses between keystrokes/clicks", "Combination typing + mouse activity",
    "No keyboard activity for long periods", "No mouse movement", "Random/irrelevant keystrokes",
    "Rapid repetitive keystrokes", "Keyboard/mouse malfunction", "Accidental touches/clicks",
    "Mouse moving off-screen repeatedly", "Typing in unrelated app", "Short bursts + idle",
    "Keyboard shortcuts", "Gesture-based input", "Copy-paste activity",
    "Multiple windows open", "External devices", "Keyboard/mouse automation",
    "Slow typing but focused reading", "Idle mouse with active keyboard"
]

# -----------------------------
# Topics / Files (~100 topics)
# -----------------------------
files = [
    # (Abbreviated: include all your previously listed 100+ files/topics here)
]

topics_cycle = itertools.cycle(files)

# -----------------------------
# Connect DB
# -----------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -----------------------------
# Clear all tables first
# -----------------------------
tables = ["sessions", "multi_modal_logs", "memory_decay", "metrics"]
for table in tables:
    cursor.execute(f"DELETE FROM {table}")
    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")  # reset AUTOINCREMENT

print("Old data cleared.")

# -----------------------------
# Populate sessions (150, avg 10min)
# -----------------------------
print("Populating sessions table...")
for _ in range(150):
    start = datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0,23))
    duration_min = random.randint(5,15)
    end = start + timedelta(minutes=duration_min)
    
    cursor.execute("""
        INSERT INTO sessions (start_ts, end_ts, app_name, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        start,
        end,
        random.choice(["VS Code", "PowerPoint", "Chrome", "Excel", "Word", "PyCharm"]),
        next(topics_cycle),
        round(random.uniform(0, 1), 2),
        random.randint(1, 20),
        random.choice(audio_scenarios),
        random.choice(eye_tracking),
        round(random.uniform(0.5,1),2)
    ))

# -----------------------------
# Populate multi-modal logs
# -----------------------------
print("Populating multi-modal logs table...")
for _ in range(200):
    ts = datetime.now() - timedelta(days=random.randint(0,30), hours=random.randint(0,23))
    cursor.execute("""
        INSERT INTO multi_modal_logs (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ts,
        next(topics_cycle),
        random.choice(ocr_scenarios),
        random.choice(audio_scenarios),
        round(random.uniform(0,1),2),
        round(random.uniform(0,1),2),
        random.choice(keyboard_mouse),
        round(random.uniform(0.5,1),2),
        round(random.uniform(0,1),2)
    ))

# -----------------------------
# Populate memory decay
# -----------------------------
print("Populating memory_decay table...")
for _ in range(100):
    last_seen = datetime.now() - timedelta(days=random.randint(0,30))
    updated_at = last_seen + timedelta(hours=random.randint(1,72))
    cursor.execute("""
        INSERT INTO memory_decay (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        next(topics_cycle),
        last_seen,
        round(random.uniform(0,1),2),
        random.randint(1,10),
        updated_at
    ))

# -----------------------------
# Populate metrics
# -----------------------------
print("Populating metrics table...")
for _ in range(100):
    next_review = datetime.now() + timedelta(days=random.randint(1,30))
    cursor.execute("""
        INSERT INTO metrics (concept, next_review_time, memory_score)
        VALUES (?, ?, ?)
    """, (
        next(topics_cycle),
        next_review,
        round(random.uniform(0,1),2),
        datetime.now()
    ))

# -----------------------------
# Commit & close
# -----------------------------
conn.commit()
conn.close()
print("Database populated successfully with new data!")
