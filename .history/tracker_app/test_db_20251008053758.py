import sqlite3
from datetime import datetime

DB_PATH = "tracker.db"  # Adjust to your actual DB path
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -----------------------
# 1️⃣ Insert dummy sessions
# -----------------------
dummy_sessions = [
    ("session1", datetime.now().isoformat(), "user1"),
    ("session2", datetime.now().isoformat(), "user2")
]

cursor.executemany(
    "INSERT INTO sessions (id, timestamp, user_id) VALUES (?, ?, ?)",
    dummy_sessions
)

# -----------------------
# 2️⃣ Insert dummy multi_modal_logs
# -----------------------
dummy_logs = [
    (
        "log1", datetime.now().isoformat(), "Window A", "keyword1,keyword2",
        "audio1", "0.8", "0.5", "intent1", "0.9", "0.7", "module1", "session1"
    ),
    (
        "log2", datetime.now().isoformat(), "Window B", "keyword3,keyword4",
        "audio2", "0.6", "0.3", "intent2", "0.85", "0.65", "module2", "session2"
    )
]

cursor.executemany(
    """
    INSERT INTO multi_modal_logs 
    (id, timestamp, window_title, ocr_keywords, audio_label, attention_score, 
     interaction_rate, intent_label, intent_confidence, memory_score, source_module, session_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    dummy_logs
)

# -----------------------
# 3️⃣ Insert dummy memory_decay
# -----------------------
dummy_memory = [
    ("session1", "memory1", 0.8, datetime.now().isoformat()),
    ("session2", "memory2", 0.6, datetime.now().isoformat())
]

cursor.executemany(
    "INSERT INTO memory_decay (session_id, memory_item, decay_value, timestamp) VALUES (?, ?, ?, ?)",
    dummy_memory
)

# -----------------------
# 4️⃣ Insert dummy metrics
# -----------------------
dummy_metrics = [
    ("session1", "attention_score", 0.75, datetime.now().isoformat()),
    ("session2", "interaction_rate", 0.55, datetime.now().isoformat())
]

cursor.executemany(
    "INSERT INTO metrics (session_id, metric_name, metric_value, timestamp) VALUES (?, ?, ?, ?)",
    dummy_metrics
)

conn.commit()
conn.close()
print("All dummy data inserted successfully!")
