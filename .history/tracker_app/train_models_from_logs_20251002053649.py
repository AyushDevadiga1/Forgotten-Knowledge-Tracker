import sqlite3
import json
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT * FROM multi_modal_logs ORDER BY id DESC LIMIT 10")
rows = c.fetchall()

for row in rows:
    # unpack row for readability
    (id, timestamp, window_title, ocr_keywords, audio_label, attention_score,
     interaction_rate, intent_label, intent_confidence) = row
     
    print(f"ID: {id}")
    print(f"Timestamp: {timestamp}")
    print(f"Window: {window_title}")
    print(f"OCR Keywords: {json.loads(ocr_keywords)}")
    print(f"Audio Label: {audio_label}")
    print(f"Attention Score: {attention_score}")
    print(f"Interaction Rate: {interaction_rate}")
    print(f"Intent Label: {intent_label}")
    print(f"Intent Confidence: {intent_confidence}")
    print("-" * 50)

conn.close()
