import sqlite3
import json
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Multi-Modal Logs
print("=== Multi-Modal Logs Table ===")
c.execute("SELECT id, timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence FROM multi_modal_logs ORDER BY id DESC LIMIT 5")
logs = c.fetchall()
for row in logs:
    log_id, timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence = row
    # Convert JSON
    ocr_data = json.loads(ocr_keywords)

    print(f"\nID: {log_id}, Time: {timestamp}, Window: {window_title}")
    print(f"Audio: {audio_label}, Attention: {attention_score}, Interaction: {interaction_rate}")
    print(f"Intent: {intent_label} ({intent_confidence:.2f})")
    print("OCR Keywords:")

    # Check type
    if isinstance(ocr_data, dict):
        for kw, info in ocr_data.items():
            if isinstance(info, dict):
                print(f"  {kw}: score={info.get('score')}, count={info.get('count')}")
            else:
                print(f"  {kw}: score={info}")
    elif isinstance(ocr_data, list):
        # older format
        for kw in ocr_data:
            print(f"  {kw}: score=unknown, count=1")

conn.close()
