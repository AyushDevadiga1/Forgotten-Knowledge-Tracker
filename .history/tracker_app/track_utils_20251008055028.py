# test_all_db.py
"""
Utility script to test and populate the Forgotten Knowledge Tracker DB.
Includes:
- Sessions logging
- Multi-modal events logging
- Memory decay updates
- Metrics logging
- Sample data insertion
"""

from core import db_module
from datetime import datetime
import random

# -----------------------------
# Initialize all tables
# -----------------------------
db_module.init_db()
db_module.init_multi_modal_db()
db_module.init_memory_decay_db()

print("✅ All tables initialized.")

# -----------------------------
# 1. Sample Sessions Logging
# -----------------------------
sample_sessions = [
    ("Visual Studio Code", 10.0, "silence", "passive", 0.98),
    ("Google Chrome", 0.0, "speech", "passive", 0.92),
    ("TestWindow", 100.0, "silence", "passive", 0.99),
]

for app_name, interaction_rate, audio_label, intent_label, intent_conf in sample_sessions:
    conn = db_module.sqlite3.connect(db_module.DB_PATH)
    c = conn.cursor()
    start_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    end_ts = start_ts
    c.execute('''
        INSERT INTO sessions 
        (start_ts, end_ts, app_name, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (start_ts, end_ts, app_name, app_name, interaction_rate, 0, audio_label, intent_label, intent_conf))
    conn.commit()
    conn.close()

print("✅ Sample sessions logged.")

# -----------------------------
# 2. Sample Multi-Modal Event Logging
# -----------------------------
sample_events = [
    ("Window A", "keyword1,keyword2", "audio1", 0.8, 0.5, "intent1", 0.9, 0.7, "module1", "session1"),
    ("Window B", "keyword3,keyword4", "audio2", 0.6, 0.3, "intent2", 0.85, 0.65, "module2", "session2"),
]

for event in sample_events:
    db_module.log_multi_modal_event(
        window_title=event[0],
        ocr_keywords=event[1],
        audio_label=event[2],
        attention_score=event[3],
        interaction_rate=event[4],
        intent_label=event[5],
        intent_confidence=event[6],
        memory_score=event[7],
        source_module=event[8]
    )

print("✅ Sample multi-modal events logged.")

# -----------------------------
# 3. Sample Memory Decay Updates
# -----------------------------
sample_memory = [
    ("Python", 2),
    ("Memory", 1),
    ("AI", 3)
]

conn = db_module.sqlite3.connect(db_module.DB_PATH)
c = conn.cursor()
for concept, usage in sample_memory:
    last_seen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    predicted_recall = random.uniform(0, 1)
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO memory_decay (concept, last_seen_ts, predicted_recall, observed_usage, updated_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (concept, last_seen, predicted_recall, usage, updated_at))
conn.commit()
conn.close()

print("✅ Sample memory decay records inserted.")

# -----------------------------
# 4. Sample Metrics Logging
# -----------------------------
conn = db_module.sqlite3.connect(db_module.DB_PATH)
c = conn.cursor()
sample_metrics = [
    ("Python", 0.05),
    ("Memory", 0.02)
]
for concept, mem_score in sample_metrics:
    next_review = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO metrics (concept, memory_score, next_review_time)
        VALUES (?, ?, ?)
    ''', (concept, mem_score, next_review))
conn.commit()
conn.close()

print("✅ Sample metrics inserted.")

# -----------------------------
# 5. Display a few rows to verify
# -----------------------------
conn = db_module.sqlite3.connect(db_module.DB_PATH)
c = conn.cursor()
print("\n--- Sample rows from 'sessions' ---")
for row in c.execute("SELECT * FROM sessions LIMIT 5"):
    print(row)

print("\n--- Sample rows from 'multi_modal_logs' ---")
for row in c.execute("SELECT * FROM multi_modal_logs LIMIT 5"):
    print(row)

print("\n--- Sample rows from 'memory_decay' ---")
for row in c.execute("SELECT * FROM memory_decay LIMIT 5"):
    print(row)

print("\n--- Sample rows from 'metrics' ---")
for row in c.execute("SELECT * FROM metrics LIMIT 5"):
    print(row)

conn.close()
print("\n✅ All tests completed successfully.")
