# test_np_to_python.py
import sqlite3
import numpy as np
import json
from config import DB_PATH

def test_logging():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create tables if not exist (just like in tracker)
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_ts TEXT,
                    end_ts TEXT,
                    app_name TEXT,
                    window_title TEXT,
                    interaction_rate REAL
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS multi_modal_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    window_title TEXT,
                    ocr_keywords TEXT,
                    audio_label TEXT,
                    attention_score REAL,
                    interaction_rate REAL,
                    intent_label TEXT,
                    intent_confidence REAL
                )''')

    conn.commit()

    # Example values, deliberately using np.int64 and np.float64
    np_interaction_rate = np.int64(1)
    np_attention_score = np.int64(2)
    np_confidence = np.float64(0.85)

    print("Types before logging:")
    print("interaction_rate:", type(np_interaction_rate))
    print("attention_score:", type(np_attention_score))
    print("intent_confidence:", type(np_confidence))

    try:
        # Attempt logging
        c.execute('''INSERT INTO multi_modal_logs
                     (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (
                      "2025-10-02 04:00:00",
                      "Test Window",
                      json.dumps(["photosynthesis", "chlorophyll"]),
                      "speech",
                      np_attention_score,
                      np_interaction_rate,
                      "studying",
                      np_confidence
                  ))
        conn.commit()
        print("Logging succeeded!")
    except Exception as e:
        print("Logging failed with error:", e)

    # Test explicit conversion to native types
    try:
        c.execute('''INSERT INTO multi_modal_logs
                     (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (
                      "2025-10-02 04:01:00",
                      "Test Window",
                      json.dumps(["photosynthesis", "chlorophyll"]),
                      "speech",
                      int(np_attention_score),
                      int(np_interaction_rate),
                      "studying",
                      float(np_confidence)
                  ))
        conn.commit()
        print("Logging with native Python types succeeded!")
    except Exception as e:
        print("Logging failed even with native types:", e)

    conn.close()

if __name__ == "__main__":
    test_logging()
