import sqlite3
from datetime impo  # adjust if needed
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Example dummy data
dummy_logs = [
    (
        "log1",  # id
        datetime.now().isoformat(),  # timestamp
        "Window A",  # window_title
        "keyword1,keyword2",  # ocr_keywords
        "audio1",  # audio_label
        "0.8",  # attention_score
        "0.5",  # interaction_rate
        "intent1",  # intent_label
        "0.9",  # intent_confidence
        "0.7",  # memory_score
        "module1",  # source_module
        "session1"  # session_id
    ),
    (
        "log2",
        datetime.now().isoformat(),
        "Window B",
        "keyword3,keyword4",
        "audio2",
        "0.6",
        "0.3",
        "intent2",
        "0.85",
        "0.65",
        "module2",
        "session2"
    )
]

cursor.executemany(
    """
    INSERT INTO multi_modal_logs 
    (id, timestamp, window_title, ocr_keywords, audio_label, attention_score, 
     interaction_rate, intent_label, intent_confidence, memory_score, source_module, session_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    dummy_logs
)

conn.commit()
conn.close()
print("Dummy data inserted successfully!")
