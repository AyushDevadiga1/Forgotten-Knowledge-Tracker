import sqlite3
import json
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# --------- Sessions ---------
print("=== Sessions Table ===")
c.execute("SELECT id, start_ts, end_ts, app_name, window_title, interaction_rate FROM sessions ORDER BY id DESC LIMIT 5")
sessions = c.fetchall()
for row in sessions:
    print(row)

# --------- Multi-Modal Logs ---------
print("\n=== Multi-Modal Logs Table ===")
c.execute("SELECT id, timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence FROM multi_modal_logs ORDER BY id DESC LIMIT 5")
logs = c.fetchall()
for row in logs:
    log_id, timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence = row
    # Convert OCR keywords JSON to Python dict
    ocr_dict = json.loads(ocr_keywords)
    print(f"\nID: {log_id}, Time: {timestamp}, Window: {window_title}")
    print(f"Audio: {audio_label}, Attention: {attention_score}, Interaction: {interaction_rate}")
    print(f"Intent: {intent_label} ({intent_confidence:.2f})")
    print(f"OCR Keywords:")
    for kw, info in ocr_dict.items():
        print(f"  {kw}: score={info.get('score')}, count={info.get('count')}")

conn.close()
