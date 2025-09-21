# Phase 5: intent classification
import sqlite3
from config import DB_PATH
from sklearn.ensemble import RandomForestClassifier
import numpy as np

# Placeholder: you can train this model later with labeled data
clf = RandomForestClassifier()

# Rule-based thresholds (simple initial implementation)
def rule_based_intent(app_name, keywords, audio_label, attention_score):
    """
    Simple rules:
    - PDF + speech + high attention -> studying
    - Browser + low attention -> distraction
    """
    if "pdf" in app_name.lower() or "word" in app_name.lower():
        if audio_label == "speech" and attention_score > 60:
            return "Studying", 0.9
        else:
            return "Passive", 0.6
    elif "chrome" in app_name.lower() or "browser" in app_name.lower():
        if attention_score < 40:
            return "Distracted", 0.8
        else:
            return "Passive", 0.5
    else:
        return "Passive", 0.5

def fetch_latest_session():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, app_name FROM sessions ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0], row[1]
    return None, None

def classify_intent():
    session_id, app_name = fetch_latest_session()
    if not session_id:
        return None, 0.0

    # Fetch latest OCR
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT keywords FROM ocr_logs WHERE session_id=? ORDER BY id DESC LIMIT 1", (session_id,))
    row = cur.fetchone()
    keywords = row[0] if row else ""

    # Fetch latest audio
    cur.execute("SELECT audio_label FROM audio_logs WHERE session_id=? ORDER BY id DESC LIMIT 1", (session_id,))
    row = cur.fetchone()
    audio_label = row[0] if row else "silence"

    # Fetch latest attention
    cur.execute("SELECT attentiveness_score FROM video_logs WHERE session_id=? ORDER BY id DESC LIMIT 1", (session_id,))
    row = cur.fetchone()
    attention_score = row[0] if row else 0

    conn.close()

    # Rule-based intent first
    label, confidence = rule_based_intent(app_name, keywords, audio_label, attention_score)

    return label, confidence
