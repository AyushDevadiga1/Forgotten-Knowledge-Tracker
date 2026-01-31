import pandas as pd
from datetime import datetime, timedelta
import random
import os

os.makedirs("test_data", exist_ok=True)

# -----------------------------
# Sessions Test Data
# -----------------------------
apps = ["VSCode", "Chrome", "YouTube", "Spotify", "Notion"]
now = datetime.now()

sessions = []
for i in range(30):
    start = now - timedelta(hours=random.randint(0, 72), minutes=random.randint(0, 59))
    end = start + timedelta(minutes=random.randint(5, 120))
    sessions.append({
        "start_ts": start.isoformat(),
        "end_ts": end.isoformat(),
        "app_name": random.choice(apps)
    })

pd.DataFrame(sessions).to_csv("test_data/sessions_test.csv", index=False)

# -----------------------------
# OCR / Logs Test Data
# -----------------------------
keywords = ["Python","Loops","Functions","Memory","Graph","Algorithm","Data","Streamlit"]
audio_labels = ["Focused","Distracted","Neutral"]
intents = ["Reading","Coding","Idle"]

logs = []
for i in range(50):
    timestamp = now - timedelta(hours=random.randint(0,72), minutes=random.randint(0,59))
    logs.append({
        "timestamp": timestamp.isoformat(),
        "ocr_keywords": str(random.sample(keywords, random.randint(0,3))),
        "audio_label": random.choice(audio_labels),
        "intent_label": random.choice(intents)
    })

pd.DataFrame(logs).to_csv("test_data/logs_test.csv", index=False)

# -----------------------------
# Memory Decay Test Data
# -----------------------------
memory_decay = []
for k in keywords:
    for i in range(10):
        ts = now - timedelta(hours=i*random.randint(1,5))
        memory_decay.append({
            "keyword": k,
            "last_seen_ts": ts.isoformat(),
            "predicted_recall": round(random.uniform(0.2,1.0),2)
        })

pd.DataFrame(memory_decay).to_csv("test_data/memory_decay_test.csv", index=False)

print("Test CSVs generated in ./test_data/")
