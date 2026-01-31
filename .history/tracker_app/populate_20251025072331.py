# populate.py
import sqlite3
import random
from datetime import datetime, timedelta
from config import DB_PATH

# Connect to DB
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -----------------------------
# Helper functions
# -----------------------------
def random_time(start, end):
    """Return random datetime between start and end"""
    delta = end - start
    int_delta = int(delta.total_seconds())
    random_second = random.randint(0, int_delta)
    return start + timedelta(seconds=random_second)

def generate_audio_label():
    return random.choice(["speech", "silence", "music", "typing", "clicks"])

def generate_intent_label():
    return random.choice(["Search Concept", "Review Note", "Quiz Attempt", "Read Article", "Watch Video"])

def generate_keywords(intent):
    base_keywords = {
        "Search Concept": ["Neural Networks", "Gradient Descent", "Activation Functions"],
        "Review Note": ["Memory Retention", "Spaced Repetition", "Learning Curve"],
        "Quiz Attempt": ["Multiple Choice", "Fill in the Blanks", "Short Answer"],
        "Read Article": ["Deep Learning", "AI Ethics", "ML Algorithms"],
        "Watch Video": ["Lecture 1", "Lecture 2", "Tutorial Video"]
    }
    return random.sample(base_keywords.get(intent, ["General"]), k=2)

# -----------------------------
# Populate sessions table
# -----------------------------
print("Populating sessions table...")
for _ in range(30):
    start_ts = datetime.now() - timedelta(days=random.randint(0, 7), hours=random.randint(0, 12))
    end_ts = start_ts + timedelta(minutes=random.randint(5, 120))
    app_name = random.choice(["Chrome", "VSCode", "Slack", "Spotify", "Notion"])
    audio_label = generate_audio_label()
    intent_label = generate_intent_label()
    intent_confidence = round(random.uniform(0.5, 1.0), 2)
    interaction_count = random.randint(1, 50)
    interaction_rate = round(random.uniform(0.1, 5.0), 2)

    cursor.execute("""
        INSERT INTO sessions
        (start_ts, end_ts, app_name, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        start_ts, end_ts, app_name, f"{app_name} - {intent_label}", interaction_rate,
        interaction_count, audio_label, intent_label, intent_confidence
    ))

# -----------------------------
# Populate multi_modal_logs table
# -----------------------------
print("Populating multi-modal logs table...")
for _ in range(50):
    timestamp = datetime.now() - timedelta(days=random.randint(0, 7), minutes=random.randint(0, 720))
    window_title = random.choice(["Chrome - Tutorial", "VSCode - Project", "Slack - Chat"])
    ocr_keywords = ", ".join(random.sample(["Python", "AI", "ML", "Graph", "Data", "Recall"], k=2))
    audio_label = generate_audio_label()
    attention_score = round(random.uniform(0, 1), 2)
    interaction_rate = round(random.uniform(0, 5), 2)
    intent_label = generate_intent_label()
    intent_confidence = round(random.uniform(0.5, 1.0), 2)
    memory_score = round(random.uniform(0.1, 1.0), 2)

    cursor.execute("""
        INSERT INTO multi_modal_logs
        (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp, window_title, ocr_keywords, audio_label, attention_score,
        interaction_rate, intent_label, intent_confidence, memory_score
    ))

# -----------------------------
# Populate memory_decay table
# -----------------------------
print("Populating memory_decay table...")
concepts = ["Neural Networks", "Spaced Repetition", "Gradient Descent", "Memory Retention", "ML Algorithms"]
for concept in concepts:
    last_seen_ts = datetime.now() - timedelta(days=random.randint(0, 10))
    predicted_recall = round(random.uniform(0, 1), 2)
    observed_usage = random.randint(1, 10)
    updated_at = datetime.now() - timedelta(days=random.randint(0, 3))

    cursor.execute("""
        INSERT INTO memory_decay
        (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        concept, last_seen_ts, predicted_recall, observed_usage, updated_at
    ))

# -----------------------------
# Populate metrics table
# -----------------------------
print("Populating metrics table...")
for concept in concepts:
    next_review_time = datetime.now() + timedelta(hours=random.randint(1, 72))
    memory_score = round(random.uniform(0.1, 1.0), 2)
    last_updated = datetime.now() - timedelta(hours=random.randint(1, 24))

    cursor.execute("""
        INSERT INTO metrics
        (concept, next_review_time, memory_score, last_updated)
        VALUES (?, ?, ?, ?)
    """, (
        concept, next_review_time, memory_score, last_updated
    ))

# Commit and close
conn.commit()
conn.close()
print("Database populated successfully!")
