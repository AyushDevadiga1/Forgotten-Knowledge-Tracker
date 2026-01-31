# test_db.py
import sqlite3
from config import DB_PATH
from datetime import datetime

# Sample data matching current multi_modal_logs columns
sample_data = [
    (
        datetime.now().isoformat(),  # timestamp
        "Test Window",               # window_title
        "keyword1, keyword2",        # ocr_keywords
        "speech_label",              # audio_label
        0.75,                        # attention_score
        0.5,                         # interaction_rate
        "intent_example",            # intent_label
        0.9,                         # intent_confidence
        0.8,                         # memory_score
        "test_module",               # source_module
        "session123"                 # session_id
    )
]

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

try:
    c.executemany('''
        INSERT INTO multi_modal_logs (
            timestamp, window_title, ocr_keywords, audio_label, attention_score,
            interaction_rate, intent_label, intent_confidence, memory_score, source_module, session_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_data)
    conn.commit()
    print("✅ Sample data inserted successfully.")
except Exception as e:
    print(f"❌ Failed to insert sample data: {e}")
finally:
    conn.close()
