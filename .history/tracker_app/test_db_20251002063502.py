# test_db.py
import sqlite3
import json
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("=== Sessions Table ===")
c.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 10")
for row in c.fetchall():
    print(row)

print("\n=== Multi-Modal Logs Table ===")
c.execute("SELECT * FROM multi_modal_logs ORDER BY id DESC LIMIT 10")
for row in c.fetchall():
    log_id, timestamp, window, ocr_json, audio_label, attention, interaction, intent_label, intent_conf = row
    
    # Safe parsing of OCR JSON
    try:
        ocr_dict = json.loads(ocr_json)
    except:
        ocr_dict = {}

    print(f"\nID: {log_id}, Time: {timestamp}, Window: {window}")
    print(f"Audio: {audio_label}, Attention: {attention}, Interaction: {interaction}")
    print(f"Intent: {intent_label} ({intent_conf:.3f})")
    print("OCR Keywords:")
    if isinstance(ocr_dict, dict) and ocr_dict:
        for kw, info in ocr_dict.items():
            score = info.get("score", 0)
            count = info.get("count", 0)
            print(f"  {kw}: score={score}, count={count}")
    else:
        print("  None")

conn.close()
