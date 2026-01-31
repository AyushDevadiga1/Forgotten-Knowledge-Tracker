# tests/populate_full_dashboard_demo.py
import sqlite3
import random
import json
import pickle
from datetime import datetime, timedelta
from core.db_module import DB_PATH, init_all_databases
from core.knowledge_graph import get_graph, add_concepts, add_edges

# -----------------------------
# CONFIG
# -----------------------------
TEST_TAG = "_TESTDATA"
DAYS = 60
START_DATE = datetime.now() - timedelta(days=DAYS)
LOGS_PER_SESSION = (5, 15)
random.seed(42)

# Apps, intents, keywords
APP_PATTERNS = {
    "VSCode": {"intents":["coding","debugging"], "keywords":["Python","ML","Tracker","Dashboard"]},
    "Chrome": {"intents":["browsing","research"], "keywords":["AI","Data","Analytics","Notebook"]},
    "Teams": {"intents":["meeting","discussion"], "keywords":["Project","Notes","Presentation"]},
    "Spotify": {"intents":["listening"], "keywords":["Music","Podcast"]},
    "Word": {"intents":["writing"], "keywords":["Report","Notes","Document"]},
}

# -----------------------------
# Helpers
# -----------------------------
def random_time(start, end):
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))

def random_window_title(app):
    return f"{app} - {random.choice(['Project','ChatGPT','Report','Presentation','Playlist'])}{TEST_TAG}"

def random_attention():
    return round(random.uniform(0.3,1.0),2)

def random_interaction_rate():
    return round(random.uniform(0.1,1.0),2)

def random_audio_label(intent):
    if intent in ["coding","debugging","writing"]:
        return "silence"
    elif intent in ["meeting","discussion"]:
        return "speech"
    else:
        return random.choice(["speech","music","silence"])

def random_memory_score():
    return round(random.uniform(0.3,1.0),2)

# -----------------------------
# Initialize DB & Graph
# -----------------------------
init_all_databases()
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
G = get_graph()

# -----------------------------
# Populate sessions & multi-modal logs
# -----------------------------
sessions = []
multi_modal_logs = []

current_day = START_DATE
while current_day <= datetime.now():
    for app, data in APP_PATTERNS.items():
        num_sessions_today = random.randint(1,3)
        for _ in range(num_sessions_today):
            start_ts = random_time(current_day, current_day + timedelta(hours=23))
            end_ts = start_ts + timedelta(minutes=random.randint(30,180))
            intent = random.choice(data["intents"])
            app_name = f"{app}{TEST_TAG}"
            window_title = random_window_title(app)
            interaction_rate = random_interaction_rate()
            interaction_count = random.randint(5,300)
            audio_label = f"{random_audio_label(intent)}{TEST_TAG}"
            intent_label = f"{intent}{TEST_TAG}"
            intent_confidence = round(random.uniform(0.5,1.0),2)

            sessions.append((start_ts.isoformat(), end_ts.isoformat(), app_name, window_title,
                             interaction_rate, interaction_count, audio_label, intent_label, intent_confidence))

            # Multi-modal logs
            num_logs = random.randint(*LOGS_PER_SESSION)
            for _ in range(num_logs):
                ts = random_time(start_ts, end_ts)
                ocr_keywords = {}
                for kw in random.sample(data["keywords"], random.randint(2,len(data["keywords"]))):
                    ocr_keywords[f"{kw}{TEST_TAG}"] = {
                        "score": round(random.uniform(0.5,1.0),2),
                        "count": random.randint(1,3)
                    }
                attention_score = random_attention()
                interaction_rate_log = random_interaction_rate()
                audio_label_log = f"{random_audio_label(intent)}{TEST_TAG}"
                intent_label_log = f"{intent}{TEST_TAG}"
                intent_confidence_log = round(random.uniform(0.5,1.0),2)
                multi_modal_logs.append((
                    ts.isoformat(), window_title, json.dumps(ocr_keywords),
                    audio_label_log, attention_score, interaction_rate_log,
                    intent_label_log, intent_confidence_log, random_memory_score()
                ))
    current_day += timedelta(days=1)

# Insert sessions
c.executemany('''
    INSERT INTO sessions (
        start_ts, end_ts, app_name, window_title,
        interaction_rate, interaction_count, audio_label, intent_label, intent_confidence
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', sessions)
conn.commit()

# Insert multi-modal logs
c.executemany('''
    INSERT INTO multi_modal_logs (
        timestamp, window_title, ocr_keywords,
        audio_label, attention_score, interaction_rate,
        intent_label, intent_confidence, memory_score
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', multi_modal_logs)
conn.commit()

# -----------------------------
# Populate memory_decay
# -----------------------------
memory_decay = []
for app, data in APP_PATTERNS.items():
    for kw in data["keywords"]:
        kw_tag = f"{kw}{TEST_TAG}"
        last_seen = random_time(START_DATE, datetime.now())
        predicted_recall = round(random.uniform(0.2,1.0),2)
        observed_usage = random.randint(1,50)
        updated_at = last_seen + timedelta(minutes=random.randint(5,120))
        memory_decay.append((kw_tag,last_seen.isoformat(),predicted_recall,observed_usage,updated_at.isoformat()))

c.executemany('''
    INSERT INTO memory_decay (
        keyword,last_seen_ts,predicted_recall,observed_usage,updated_at
    ) VALUES (?, ?, ?, ?, ?)
''', memory_decay)
conn.commit()

# -----------------------------
# Populate metrics
# -----------------------------
metrics = []
for app, data in APP_PATTERNS.items():
    for kw in data["keywords"]:
        kw_tag = f"{kw}{TEST_TAG}"
        next_review = datetime.now() + timedelta(hours=random.randint(1,336))
        memory_score = round(random.uniform(0.3,1.0),2)
        last_updated = datetime.now() - timedelta(days=random.randint(0,14))
        metrics.append((kw_tag,next_review.isoformat(),memory_score,last_updated.isoformat()))

c.executemany('''
    INSERT INTO metrics (
        concept,next_review_time,memory_score,last_updated
    ) VALUES (?, ?, ?, ?)
''', metrics)
conn.commit()

conn.close()

# -----------------------------
# Populate knowledge graph
# -----------------------------
for app, data in APP_PATTERNS.items():
    for intent in data["intents"]:
        for kw in data["keywords"]:
            kw_tag = f"{kw}{TEST_TAG}"
            intent_tag = f"{intent}{TEST_TAG}"
            add_concepts([kw_tag, intent_tag])
            for _ in range(random.randint(1,3)):
                add_edges({kw_tag: {"score": round(random.uniform(0.5,1.0),2), "count": random.randint(1,3)}},
                          audio_label=f"{random.choice(['speech','silence','music'])}{TEST_TAG}",
                          intent_label=intent_tag)
            if kw_tag in G.nodes:
                G.nodes[kw_tag]['memory_score'] = round(random.uniform(0.3,1.0),2)
            if intent_tag in G.nodes:
                G.nodes[intent_tag]['memory_score'] = round(random.uniform(0.3,1.0),2)

# Save graph
with open("data/knowledge_graph.pkl", "wb") as f:
    pickle.dump(G, f)

print("✅ Dashboard demo data populated (sessions, logs, memory, metrics, knowledge graph)")

# -----------------------------
# Cleanup functions
# -----------------------------
def cleanup_test_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    tables = ["sessions", "multi_modal_logs", "memory_decay", "metrics"]
    for table in tables:
        for col in ("app_name","window_title","ocr_keywords","intent_label","audio_label","keyword","concept"):
            try:
                c.execute(f"DELETE FROM {table} WHERE {col} LIKE '%{TEST_TAG}%'")
            except sqlite3.OperationalError:
                continue
    conn.commit()
    conn.close()
    print(f"✅ DB cleanup done for '{TEST_TAG}'")

def cleanup_test_graph():
    G = get_graph()
    to_remove = [n for n in G.nodes if n.endswith(TEST_TAG)]
    for n in to_remove:
        G.remove_node(n)
    with open("data/knowledge_graph.pkl", "wb") as f:
        pickle.dump(G, f)
    print(f"✅ Graph cleanup done for '{TEST_TAG}'")

# Uncomment below lines to cleanup
# cleanup_test_db()
# cleanup_test_graph()
