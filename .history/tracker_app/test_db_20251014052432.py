# tests/populate_stress_test_data.py
import sqlite3
import random
import json
from datetime import datetime, timedelta
from core.db_module import DB_PATH, init_all_databases

# Initialize DB tables
init_all_databases()
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ---------------------------
# Helper functions
# ---------------------------
def random_time(start, end):
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))

def random_app():
    return random.choice(["TEST_APP_Chrome","TEST_APP_VSCode","TEST_APP_Slack","TEST_APP_Spotify","TEST_APP_Word"])

def random_window_title():
    return random.choice([
        "TEST_Chrome - ChatGPT", "TEST_VSCode - Project FKT", 
        "TEST_Slack - Team Chat", "TEST_Spotify - Playlist", "TEST_Word - Report.docx"
    ])

def random_ocr_keywords():
    words = ["TEST_Python","TEST_ML","TEST_Tracker","TEST_Memory","TEST_Dashboard","TEST_AI","TEST_Session"]
    return {word: {"score": round(random.uniform(0.5,1.0),2), "count": random.randint(1,3)}
            for word in random.sample(words, random.randint(2,5))}

def random_intent():
    intents = ["note_taking","research","listening","coding","browsing"]
    intent = random.choice(intents)
    confidence = round(random.uniform(0.5,1.0),2)
    return intent, confidence

def random_audio_label():
    return random.choice(["speech","silence","music","noise"])

# ---------------------------
# Populate sessions (~50)
# ---------------------------
num_sessions = 50
start_date = datetime.now() - timedelta(days=14)  # 2 weeks
sessions = []

for _ in range(num_sessions):
    start_ts = random_time(start_date, datetime.now() - timedelta(minutes=10))
    end_ts = start_ts + timedelta(minutes=random.randint(5, 60))
    app_name = random_app()
    window_title = random_window_title()
    interaction_rate = round(random.uniform(0.1, 1.0), 2)
    interaction_count = random.randint(1, 50)
    audio_label = random_audio_label()
    intent_label, intent_confidence = random_intent()
    
    sessions.append((start_ts.isoformat(), end_ts.isoformat(), app_name, window_title,
                     interaction_rate, interaction_count, audio_label, intent_label, intent_confidence))

c.executemany('''
    INSERT INTO sessions (
        start_ts, end_ts, app_name, window_title,
        interaction_rate, interaction_count, audio_label, intent_label, intent_confidence
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', sessions)
conn.commit()

# ---------------------------
# Populate multi-modal logs (~200)
# ---------------------------
multi_modal_logs = []
for sess in sessions:
    sess_start = datetime.fromisoformat(sess[0])
    for _ in range(random.randint(3,6)):
        ts = sess_start + timedelta(minutes=random.randint(0, int((datetime.fromisoformat(sess[1])-sess_start).total_seconds()//60)))
        ocr_keywords = random_ocr_keywords()
        audio_label = random_audio_label()
        attention_score = round(random.uniform(0,1),2)
        interaction_rate = round(random.uniform(0,1),2)
        intent_label, intent_confidence = random_intent()
        memory_score = round(random.uniform(0.3,1.0),2)
        
        multi_modal_logs.append((
            ts.isoformat(), random_window_title(), json.dumps(ocr_keywords),
            audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score
        ))

c.executemany('''
    INSERT INTO multi_modal_logs (
        timestamp, window_title, ocr_keywords,
        audio_label, attention_score, interaction_rate,
        intent_label, intent_confidence, memory_score
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', multi_modal_logs)
conn.commit()

# ---------------------------
# Populate memory_decay (~10 keywords)
# ---------------------------
memory_decay = []
keywords = ["TEST_Python","TEST_ML","TEST_Tracker","TEST_Memory","TEST_Dashboard","TEST_AI","TEST_Session","TEST_Concept1","TEST_Concept2","TEST_Concept3"]
for kw in keywords:
    last_seen = random_time(start_date, datetime.now())
    predicted_recall = round(random.uniform(0.2, 1.0),2)
    observed_usage = random.randint(1,5)
    updated_at = last_seen + timedelta(minutes=random.randint(5,120))
    memory_decay.append((kw,last_seen.isoformat(),predicted_recall,observed_usage,updated_at.isoformat()))

c.executemany('''
    INSERT INTO memory_decay (
        keyword,last_seen_ts,predicted_recall,observed_usage,updated_at
    ) VALUES (?, ?, ?, ?, ?)
''', memory_decay)
conn.commit()

# ---------------------------
# Populate metrics (~10 reminders)
# ---------------------------
metrics = []
for kw in keywords:
    next_review = datetime.now() + timedelta(hours=random.randint(1,72))
    memory_score = round(random.uniform(0.3,1.0),2)
    last_updated = datetime.now() - timedelta(days=random.randint(0,7))
    metrics.append((kw,next_review.isoformat(),memory_score,last_updated.isoformat()))

c.executemany('''
    INSERT INTO metrics (
        concept,next_review_time,memory_score,last_updated
    ) VALUES (?, ?, ?, ?)
''', metrics)
conn.commit()
conn.close()

print("Stress-test data inserted! ✅")
print("All test data is tagged with 'TEST_' and can be deleted safely later with:")
print("DELETE FROM sessions WHERE app_name LIKE 'TEST_%';")
print("DELETE FROM multi_modal_logs WHERE window_title LIKE 'TEST_%';")
print("DELETE FROM memory_decay WHERE keyword LIKE 'TEST_%';")
print("DELETE FROM metrics WHERE concept LIKE 'TEST_%';")
