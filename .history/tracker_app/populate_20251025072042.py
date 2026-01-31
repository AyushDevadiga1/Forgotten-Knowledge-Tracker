# test_data_populate_full.py
import sqlite3
from datetime import datetime, timedelta
import random
import json
from config import DB_PATH

# -----------------------------
# Utility: Random timestamp generator
# -----------------------------
def random_time(start, end):
    """Generate random datetime between start and end"""
    return start + timedelta(seconds=random.randint(0, int((end-start).total_seconds())))

# -----------------------------
# Test Data Parameters
# -----------------------------
apps = ["VS Code", "Chrome", "Spotify", "Slack", "Jupyter Notebook", "YouTube", "PyCharm", "Notepad++"]
window_titles = {
    "VS Code": ["tracker.py", "FKT module", "analysis.py", "data_loader.py"],
    "Chrome": ["Wikipedia ML", "YouTube Data Science", "Reddit AI", "StackOverflow Python"],
    "Spotify": ["Ambient", "Lo-fi Beats", "Focus Playlist"],
    "Slack": ["Team Chat", "Project Discussion", "Random Channel"],
    "Jupyter Notebook": ["ML Notebook", "Data Analysis", "Visualization Notebook"],
    "YouTube": ["ML Tutorial", "Data Science Talk", "Coding Stream"],
    "PyCharm": ["FKT Project", "Test Module", "ML Script"],
    "Notepad++": ["Notes.txt", "Ideas.txt", "Todo.txt"]
}

audio_labels = ["speech", "silence", "music", "typing"]
intents = ["coding", "learning", "research", "idle", "chatting", "browsing"]
keywords_pool = ["python", "sqlite3", "graphs", "memory", "learning", "data", "analysis", "ML", "AI", "visualization"]

# -----------------------------
# Connect to DB
# -----------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -----------------------------
# Clear old data
# -----------------------------
cursor.execute("DELETE FROM sessions")
cursor.execute("DELETE FROM multi_modal_logs")
cursor.execute("DELETE FROM memory_decay")
cursor.execute("DELETE FROM metrics")
conn.commit()

# -----------------------------
# Insert Sessions & Multi-Modal Logs
# -----------------------------
start_date = datetime.now() - timedelta(days=7)

for _ in range(250):  # 250 diverse sessions
    app = random.choice(apps)
    window = random.choice(window_titles[app])
    audio = random.choice(audio_labels)
    intent = random.choice(intents)
    start_ts = random_time(start_date, datetime.now() - timedelta(minutes=5))
    end_ts = start_ts + timedelta(minutes=random.randint(5, 120))
    interaction_rate = round(random.uniform(0, 10), 2)
    interaction_count = random.randint(0, 20)
    intent_conf = round(random.uniform(0.5, 1.0), 2)

    # Insert into sessions
    cursor.execute("""
        INSERT INTO sessions
        (start_ts, end_ts, app_name, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (start_ts, end_ts, app, window, interaction_rate, interaction_count, audio, intent, intent_conf))

    # Insert multiple multi-modal logs per session to simulate dense data
    for _ in range(random.randint(1, 4)):
        ts = start_ts + timedelta(seconds=random.randint(0, int((end_ts - start_ts).total_seconds())))
        ocr_keywords = random.sample(keywords_pool, random.randint(1, 4))
        attention_score = round(random.uniform(0,1),2)
        memory_score = round(random.uniform(0,1),2)
        cursor.execute("""
            INSERT INTO multi_modal_logs
            (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ts, window, json.dumps(ocr_keywords), audio, attention_score, interaction_rate, intent, intent_conf, memory_score))

# -----------------------------
# Insert Memory Decay
# -----------------------------
for keyword in keywords_pool:
    for _ in range(random.randint(2,5)):  # multiple decay records per keyword
        last_seen = random_time(start_date, datetime.now())
        predicted_recall = round(random.uniform(0.1, 0.95),2)
        observed_usage = random.randint(1, 15)
        updated_at = last_seen + timedelta(minutes=random.randint(10, 500))
        cursor.execute("""
            INSERT INTO memory_decay
            (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (keyword, last_seen, predicted_recall, observed_usage, updated_at))

# -----------------------------
# Insert Metrics / Upcoming Reminders
# -----------------------------
for keyword in keywords_pool:
    for _ in range(random.randint(1,3)):  # multiple reminders per concept
        next_review = datetime.now() + timedelta(hours=random.randint(1,72))
        memory_score = round(random.uniform(0.1, 1.0),2)
        last_updated = datetime.now() - timedelta(days=random.randint(0,3))
        cursor.execute("""
            INSERT INTO metrics
            (concept, next_review_time, memory_score, last_updated)
            VALUES (?, ?, ?, ?)
        """, (keyword, next_review, memory_score, last_updated))

conn.commit()
conn.close()
print("Full test data inserted successfully. Dashboard should now display a dense, realistic dataset.")
