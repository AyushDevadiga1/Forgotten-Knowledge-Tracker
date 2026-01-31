import sqlite3
from datetime import datetime, timedelta
import random
import string
import numpy as np
import pandas as pd
from config import DB_PATH

# -----------------------------
# Utility Functions
# -----------------------------
def random_string(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def random_concept():
    concepts = ["Python", "ML", "Deep Learning", "Databases", "Algorithms", "FKT System", "Streamlit", "NLP", "Graph Theory"]
    return random.choice(concepts)

def random_intent():
    intents = ["Learn", "Review", "Practice", "Test", "Summarize"]
    return random.choice(intents)

def random_app():
    apps = ["VSCode", "Chrome", "Notion", "Jupyter", "Spotify"]
    return random.choice(apps)

# -----------------------------
# Connect to DB
# -----------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -----------------------------
# Create Tables if Not Exists
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    app_name TEXT,
    start_ts TEXT,
    end_ts TEXT,
    intent_label TEXT,
    intent_confidence REAL,
    audio_label TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS multi_modal_logs (
    log_id TEXT PRIMARY KEY,
    session_id TEXT,
    timestamp TEXT,
    modality TEXT,
    value TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS memory_decay (
    keyword TEXT PRIMARY KEY,
    last_seen_ts TEXT,
    predicted_recall REAL,
    updated_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS metrics (
    concept TEXT PRIMARY KEY,
    next_review_time TEXT,
    memory_score REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS multi_modal_keywords (
    intent_label TEXT,
    keyword TEXT
)
""")

# -----------------------------
# Insert Random Data
# -----------------------------
num_sessions = 100
num_keywords = 50

sessions = []
logs = []
decays = []
metrics = []
keywords = []

now = datetime.now()

# Sessions & Multi-modal logs
for i in range(num_sessions):
    start = now - timedelta(days=random.randint(0, 30), hours=random.randint(0,23), minutes=random.randint(0,59))
    duration = timedelta(minutes=random.randint(5, 60))
    end = start + duration
    session_id = f"S{i+1:04d}"
    intent = random_intent()
    app = random_app()
    confidence = round(random.uniform(0.5, 1.0),2)
    audio_label = random_string(3)

    sessions.append((session_id, app, start.isoformat(), end.isoformat(), intent, confidence, audio_label))

    # Each session has 1-5 multi-modal logs
    for j in range(random.randint(1,5)):
        log_id = f"L{i+1:03d}_{j+1}"
        timestamp = start + timedelta(minutes=random.randint(0,int(duration.total_seconds()/60)))
        modality = random.choice(["audio", "video", "text"])
        value = random_string(5)
        logs.append((log_id, session_id, timestamp.isoformat(), modality, value))

# Memory Decay & Metrics
for i in range(num_keywords):
    concept = random_concept()
    last_seen = now - timedelta(days=random.randint(0,30))
    score = round(random.uniform(0.3, 1.0),2)
    decays.append((concept, last_seen.isoformat(), score, now.isoformat()))
    next_review = now + timedelta(days=random.randint(1,10))
    metrics.append((concept, next_review.isoformat(), score))

# Keywords table
for i in range(num_keywords):
    intent = random_intent()
    keyword = random_concept() + "_" + random_string(3)
    keywords.append((intent, keyword))

# -----------------------------
# Insert into DB
# -----------------------------
cursor.executemany("INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?,?)", sessions)
cursor.executemany("INSERT OR REPLACE INTO multi_modal_logs VALUES (?,?,?,?,?)", logs)
cursor.executemany("INSERT OR REPLACE INTO memory_decay VALUES (?,?,?,?)", decays)
cursor.executemany("INSERT OR REPLACE INTO metrics VALUES (?,?,?)", metrics)
cursor.executemany("INSERT OR REPLACE INTO multi_modal_keywords VALUES (?,?)", keywords)

conn.commit()
conn.close()
print("✅ Random test data inserted successfully!")
