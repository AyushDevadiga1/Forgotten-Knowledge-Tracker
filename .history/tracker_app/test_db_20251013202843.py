import sqlite3
from datetime import datetime, timedelta
import random
import string
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
# Generate Random Data
# -----------------------------
num_sessions = 100
num_keywords = 50
now = datetime.now()

sessions = []
multi_logs = []
memory_decay = []
metrics = []

for i in range(num_sessions):
    start = now - timedelta(days=random.randint(0, 30), hours=random.randint(0,23), minutes=random.randint(0,59))
    duration = timedelta(minutes=random.randint(5, 60))
    end = start + duration
    app = random_app()
    window_title = random_string(8)
    interaction_rate = round(random.uniform(0.1, 1.0),2)
    interaction_count = random.randint(1,50)
    audio_label = random_string(3)
    intent_label = random_intent()
    intent_confidence = round(random.uniform(0.5, 1.0),2)

    sessions.append((start.isoformat(), end.isoformat(), app, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence))

    # Multi-modal logs per session
    for j in range(random.randint(1,5)):
        timestamp = start + timedelta(minutes=random.randint(0,int(duration.total_seconds()/60)))
        window_title_log = window_title
        ocr_keywords = random_string(4)
        audio_label_log = random_string(3)
        attention_score = round(random.uniform(0,1),2)
        interaction_rate_log = round(random.uniform(0,1),2)
        intent_label_log = intent_label
        intent_confidence_log = intent_confidence
        memory_score = round(random.uniform(0.3,1.0),2)

        multi_logs.append((timestamp.isoformat(), window_title_log, ocr_keywords, audio_label_log, attention_score,
                           interaction_rate_log, intent_label_log, intent_confidence_log, memory_score))

# Memory Decay
for i in range(num_keywords):
    keyword = random_concept()
    last_seen_ts = now - timedelta(days=random.randint(0,30))
    predicted_recall = round(random.uniform(0.3,1.0),2)
    observed_usage = random.randint(1,10)
    updated_at = now
    memory_decay.append((keyword, last_seen_ts.isoformat(), predicted_recall, observed_usage, updated_at.isoformat()))

# Metrics
for i in range(num_keywords):
    concept = random_concept()
    next_review_time = now + timedelta(days=random.randint(1,10))
    memory_score = round(random.uniform(0.3,1.0),2)
    last_updated = now
    metrics.append((concept, next_review_time.isoformat(), memory_score, last_updated.isoformat()))

# -----------------------------
# Insert Data
# -----------------------------
cursor.executemany("""
    INSERT INTO sessions 
    (start_ts, end_ts, app_name, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence)
    VALUES (?,?,?,?,?,?,?,?,?)
""", sessions)

cursor.executemany("""
    INSERT INTO multi_modal_logs
    (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
    VALUES (?,?,?,?,?,?,?,?,?)
""", multi_logs)

cursor.executemany("""
    INSERT INTO memory_decay
    (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
    VALUES (?,?,?,?,?)
""", memory_decay)

cursor.executemany("""
    INSERT INTO metrics
    (concept, next_review_time, memory_score, last_updated)
    VALUES (?,?,?,?)
""", metrics)

conn.commit()
conn.close()
print("✅ Random test data inserted successfully!")
