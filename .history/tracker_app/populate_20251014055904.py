# populate_demo_data.py
import sqlite3
import random
import json
from datetime import datetime, timedelta
from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db, init_metrics_db
from config import DB_PATH
from core.knowledge_graph import get_graph, add_concepts, add_edges

# -----------------------------
# Initialize all tables
# -----------------------------
init_db()
init_multi_modal_db()
init_memory_decay_db()
init_metrics_db()

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# -----------------------------
# Helper variables
# -----------------------------
apps = ["Chrome", "Word", "Excel", "VSCode", "PowerPoint", "Slack", "Spotify"]
window_titles = ["Research Paper", "Project Notes", "Budget Sheet", "Code Editor", "Presentation Slides", "Team Chat", "Music Playlist"]
audio_labels = ["speech", "music", "silence"]
intents = ["Study", "Work", "Entertainment", "Meeting", "Coding", "Review"]
ocr_keywords_samples = ["linear algebra", "neural networks", "deep learning", "Python functions", "finance report", "marketing strategy"]
memory_concepts = ["linear algebra", "neural networks", "Python functions", "finance report", "marketing strategy", "project planning"]

start_date = datetime.now() - timedelta(days=60)  # last 2 months

# -----------------------------
# Populate sessions table
# -----------------------------
for day in range(60):
    date_base = start_date + timedelta(days=day)
    num_sessions = random.randint(3, 7)
    for s in range(num_sessions):
        start_offset = timedelta(minutes=random.randint(8*60, 22*60))  # between 8 AM and 10 PM
        duration = timedelta(minutes=random.randint(5, 90))  # realistic session durations
        start_ts = date_base + start_offset
        end_ts = start_ts + duration
        app_name = random.choice(apps)
        window_title = random.choice(window_titles) + "__TEST__"
        interaction_rate = round(random.uniform(0, 20), 2)
        interaction_count = random.randint(0, 100)
        audio_label = random.choice(audio_labels)
        intent_label = random.choice(intents) + "__TEST__"
        intent_confidence = round(random.uniform(0.5, 1.0), 2)

        c.execute('''
            INSERT INTO sessions
            (start_ts, end_ts, app_name, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            start_ts.isoformat(), end_ts.isoformat(), app_name, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence
        ))

conn.commit()

# -----------------------------
# Populate multi_modal_logs table
# -----------------------------
for day in range(60):
    date_base = start_date + timedelta(days=day)
    num_logs = random.randint(5, 12)
    for l in range(num_logs):
        timestamp = date_base + timedelta(minutes=random.randint(0, 1439))
        window_title = random.choice(window_titles) + "__TEST__"
        ocr_keywords = {kw + "__TEST__": {"score": round(random.uniform(0.5, 1.0), 2), "count": random.randint(1,5)}
                        for kw in random.sample(ocr_keywords_samples, random.randint(1,3))}
        audio_label = random.choice(audio_labels)
        attention_score = round(random.uniform(0,1), 2)
        interaction_rate = round(random.uniform(0,20), 2)
        intent_label = random.choice(intents) + "__TEST__"
        intent_confidence = round(random.uniform(0.5, 1.0), 2)
        memory_score = round(random.uniform(0,1), 2)

        c.execute('''
            INSERT INTO multi_modal_logs
            (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp.isoformat(), window_title, json.dumps(ocr_keywords), audio_label, attention_score,
            interaction_rate, intent_label, intent_confidence, memory_score
        ))

conn.commit()

# -----------------------------
# Populate memory_decay table
# -----------------------------
for concept in memory_concepts:
    for i in range(5):  # multiple entries per concept
        last_seen_ts = start_date + timedelta(days=random.randint(0, 59), hours=random.randint(0,23))
        predicted_recall = round(random.uniform(0.3, 1.0), 2)
        observed_usage = random.randint(1,5)
        updated_at = last_seen_ts + timedelta(hours=random.randint(1,24))

        c.execute('''
            INSERT INTO memory_decay
            (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            concept + "__TEST__", last_seen_ts.isoformat(), predicted_recall, observed_usage, updated_at.isoformat()
        ))

conn.commit()

# -----------------------------
# Populate metrics table (reminders)
# -----------------------------
for concept in memory_concepts:
    for i in range(2):
        next_review_time = datetime.now() + timedelta(days=random.randint(1,30))
        memory_score = round(random.uniform(0,1),2)
        last_updated = datetime.now() - timedelta(days=random.randint(0,30))

        c.execute('''
            INSERT INTO metrics
            (concept, next_review_time, memory_score, last_updated)
            VALUES (?, ?, ?, ?)
        ''', (
            concept + "__TEST__", next_review_time.isoformat(), memory_score, last_updated.isoformat()
        ))

conn.commit()
conn.close()

# -----------------------------
# Update knowledge graph with all OCR keywords
# -----------------------------
all_keywords = [kw + "__TEST__" for kw in ocr_keywords_samples]
add_concepts(all_keywords)
print("Database populated successfully for demo with realistic data (all entries marked __TEST__)")
