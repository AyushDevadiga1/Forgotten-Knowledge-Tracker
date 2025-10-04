# test_db_safe.py
import sqlite3
import json
from config import DB_PATH

def fetch_sessions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    print("=== Sessions Table ===")
    for row in rows:
        print(row)

def fetch_multi_modal_logs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM multi_modal_logs ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()

    print("\n=== Multi-Modal Logs Table ===")
    for row in rows:
        id, ts, window, ocr_json, audio, attention, interaction, intent, intent_conf = row
        try:
            ocr_dict = json.loads(ocr_json)
            if not isinstance(ocr_dict, dict):
                ocr_dict = {}
        except Exception:
            ocr_dict = {}

        print(f"\nID: {id}, Time: {ts}, Window: {window}")
        print(f"Audio: {audio}, Attention: {float(attention)}, Interaction: {float(interaction)}")
        print(f"Intent: {intent} ({float(intent_conf)})")
        print("OCR Keywords:")
        for kw, info in ocr_dict.items():
            print(f"  {kw}: score={float(info.get('score', 0))}, count={int(info.get('count', 0))}")

if __name__ == "__main__":
    fetch_sessions()
    fetch_multi_modal_logs()
