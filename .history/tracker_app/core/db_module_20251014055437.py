# populate_realistic_demo_db_full.py
import sqlite3
import random
import json
import os
import pickle
from datetime import datetime, timedelta
from core.db_module import init_all_databases
from core.knowledge_graph import get_graph, add_concepts, add_edges

# -----------------------------
# CONFIG
# -----------------------------
from config import DB_PATH

# -----------------------------
# Initialize DB tables
# -----------------------------
init_all_databases()

# -----------------------------
# HELPERS
# -----------------------------
def random_time(start, end):
    """Return a random datetime between start and end"""
    delta = end - start
    seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=seconds)

def cleanup_demo_data():
    """Remove all demo data marked with '_DEMO' suffix"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    tables = ['sessions', 'multi_modal_logs', 'memory_decay', 'metrics']
    for table in tables:
        c.execute(f"DELETE FROM {table} WHERE app_name LIKE '%_DEMO' OR window_title LIKE '%_DEMO' OR concept LIKE '%_DEMO' OR keyword LIKE '%_DEMO'")
    conn.commit()
    conn.close()
    print("Demo data cleaned up.")

# -----------------------------
# REALISTIC DATA PARAMETERS
# -----------------------------
apps = ['Chrome', 'VSCode', 'Spotify', 'Slack', 'Excel', 'Word', 'Edge']
intents = ['Study', 'Meeting', 'Entertainment', 'Research', 'Coding']
audio_labels = ['speech', 'music', 'silence']
keywords_list = ['Python', 'AI', 'NeuralNet', 'SQL', 'DataFrame', 'Regression', 'Matplotlib']

start_date = datetime.now() - timedelta(days=60)
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# -----------------------------
# Populate Sessions & Multi-Modal Logs
# -----------------------------
for day_offset in range(60):
    current_day = start_date + timedelta(days=day_offset)
    for app in apps:
        for _ in range(random.randint(2,5)):  # 2-5 sessions per app per day
            start_hour = random.randint(8, 22)
            start_minute = random.randint(0, 59)
            start_ts = current_day.replace(hour=start_hour, minute=start_minute, second=random.randint(0,59))
            end_ts = start_ts + timedelta(minutes=random.randint(30, 180))

            interaction_rate = round(random.uniform(0.1, 5.0), 2)
            interaction_count = random.randint(5, 500)
            audio_label = random.choices(audio_labels, weights=[0.5,0.2,0.3])[0]
            intent_label = random.choice(intents)
            intent_confidence = round(random.uniform(0.5,1.0),2)
            app_name = f"{app}_DEMO"
            window_title = f"{app} - Window_DEMO"

            # Insert into sessions
            c.execute('''INSERT INTO sessions 
                         (start_ts, end_ts, app_name, window_title, interaction_rate, interaction_count,
                          audio_label, intent_label, intent_confidence)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (start_ts.strftime("%Y-%m-%d %H:%M:%S"),
                       end_ts.strftime("%Y-%m-%d %H:%M:%S"),
                       app_name,
                       window_title,
                       interaction_rate,
                       interaction_count,
                       audio_label,
                       intent_label,
                       intent_confidence))

            # Multi-Modal logs per session
            num_logs = random.randint(1,5)
            for _ in range(num_logs):
                log_ts = random_time(start_ts, end_ts)
                ocr_keywords = {kw: {"score": round(random.uniform(0.5,1.0),2), "count": random.randint(1,3)} 
                                for kw in random.sample(keywords_list, random.randint(1,3))}
                attention_score = round(random.uniform(0.4,1.0) if app != "Spotify" else random.uniform(0.1,0.6),2)
                memory_score = round(random.uniform(0.0,1.0),2)
                c.execute('''INSERT INTO multi_modal_logs
                             (timestamp, window_title, ocr_keywords, audio_label, attention_score,
                              interaction_rate, intent_label, intent_confidence, memory_score)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (log_ts.strftime("%Y-%m-%d %H:%M:%S"),
                           window_title,
                           json.dumps(ocr_keywords),
                           audio_label,
                           attention_score,
                           interaction_rate,
                           intent_label,
                           intent_confidence,
                           memory_score))

# -----------------------------
# Memory Decay
# -----------------------------
for kw in keywords_list:
    for i in range(5):
        last_seen_ts = start_date + timedelta(days=random.randint(0,59), hours=random.randint(0,23))
        predicted_recall = round(random.uniform(0.1,1.0),2)
        observed_usage = random.randint(1,10)
        updated_at = last_seen_ts + timedelta(hours=random.randint(1,12))
        c.execute('''INSERT INTO memory_decay
                     (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
                     VALUES (?, ?, ?, ?, ?)''',
                  (f"{kw}_DEMO",
                   last_seen_ts.strftime("%Y-%m-%d %H:%M:%S"),
                   predicted_recall,
                   observed_usage,
                   updated_at.strftime("%Y-%m-%d %H:%M:%S")))

# -----------------------------
# Metrics / Reminders
# -----------------------------
for kw in keywords_list:
    next_review_time = datetime.now() + timedelta(days=random.randint(0,10))
    memory_score = round(random.uniform(0.0,1.0),2)
    last_updated = datetime.now() - timedelta(days=random.randint(0,5))
    c.execute('''INSERT INTO metrics
                 (concept, next_review_time, memory_score, last_updated)
                 VALUES (?, ?, ?, ?)''',
              (f"{kw}_DEMO",
               next_review_time.strftime("%Y-%m-%d %H:%M:%S"),
               memory_score,
               last_updated.strftime("%Y-%m-%d %H:%M:%S")))

conn.commit()
conn.close()
print("✅ Realistic demo database populated for 2 months. Use cleanup_demo_data() to remove demo entries.")

# -----------------------------
# Knowledge Graph Pre-Population
# -----------------------------
G = get_graph()
for kw in keywords_list:
    for i in range(3):
        concept = f"{kw}_DEMO"
        add_concepts([concept])
        # connect each concept to random intents
        for intent in intents:
            edge_label = f"{intent}_DEMO"
            add_edges({concept: {"score": random.uniform(0.5,1.0), "count":1}}, audio_label=random.choice(audio_labels), intent_label=edge_label)

# Save knowledge graph
os.makedirs("data", exist_ok=True)
with open("data/knowledge_graph.pkl","wb") as f:
    pickle.dump(G, f)

print("✅ Knowledge graph pre-populated with demo concepts and edges.")
