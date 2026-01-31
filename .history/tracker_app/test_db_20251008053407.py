import sqlite3
from datetime import datetime, timedelta
import random
from conf
DB_PATH  # update with your actual DB path

# --- Connect to DB ---
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# --- Fetch existing sessions ---
cursor.execute("SELECT id FROM sessions")
sessions = [row[0] for row in cursor.fetchall()]

# --- Create dummy multi-modal logs ---
event_types = ["text", "image", "video", "audio"]
dummy_logs = []

for session_id in sessions:
    # Create 3-5 dummy events per session
    for i in range(random.randint(3, 5)):
        event_type = random.choice(event_types)
        content = f"Dummy {event_type} content for session {session_id}, event {i+1}"
        timestamp = datetime.now() - timedelta(days=random.randint(0, 10))
        dummy_logs.append((session_id, event_type, content, timestamp.strftime("%Y-%m-%d %H:%M:%S")))

# --- Insert logs into multi_modal_logs ---
cursor.executemany(
    "INSERT INTO multi_modal_logs (session_id, event_type, content, timestamp) VALUES (?, ?, ?, ?)",
    dummy_logs
)
conn.commit()
print(f"✅ Inserted {len(dummy_logs)} dummy multi-modal logs.")

# --- Optional: Check if logs were inserted ---
cursor.execute("SELECT COUNT(*) FROM multi_modal_logs")
total_logs = cursor.fetchone()[0]
print(f"Total logs in multi_modal_logs: {total_logs}")

conn.close()
