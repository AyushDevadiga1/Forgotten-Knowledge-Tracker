import sqlite3
import json
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ---- Sessions Table ----
print("=== Sessions Table ===")
c.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 10")
rows = c.fetchall()
for row in rows:
    print(row)

# ---- Multi-Modal Logs Table ----
print("\n=== Multi-Modal Logs Table ===")
c.execute("SELECT * FROM multi_modal_logs ORDER BY id DESC LIMIT 10")
rows = c.fetchall()
for row in rows:
    id, timestamp, window, ocr_json, audio, attention, interaction, intent_label, intent_conf = row
    print(f"\nID: {id}, Time: {timestamp}, Window: {window}")
    print(f"Audio: {audio}, Attention: {attention}, Interaction: {interaction}")
    print(f"Intent: {intent_label} ({intent_conf})")
    
    try:
        ocr_dict = json.loads(ocr_json)
        if isinstance(ocr_dict, dict) and ocr_dict:
            print("OCR Keywords:")
            for kw, info in ocr_dict.items():
                score = info.get("score", 0.0)
                count = info.get("count", 0)
                print(f"  {kw}: score={score:.2f}, count={count}")
        else:
            print("OCR Keywords: None")
    except Exception as e:
        print(f"OCR Keywords: Error parsing JSON ({e})")

conn.close()
