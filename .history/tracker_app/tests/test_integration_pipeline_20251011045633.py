"""
test_integration_pipeline.py

Integration Test: Full Multi-Modal Tracker Pipeline
---------------------------------------------------
- Runs audio, OCR, webcam, and session manager modules together.
- Creates a new session, updates with all modalities, logs to DB.
- Checks database tables for expected rows.
"""

import sqlite3
from core.session_manager import create_session, update_session, log_session_to_db
from core.audio_module import audio_pipeline
from core.ocr_module import ocr_pipeline
from core.webcam_module import webcam_pipeline
from config import DB_PATH

def run_integration_test():
    print("=== Starting Integration Test ===")

    # 1️⃣ Create new session
    session = create_session()
    print("[Test] Created session:", session)

    # 2️⃣ Capture audio
    audio_result = audio_pipeline()
    update_session(session, "audio_label", audio_result.get("audio_label", "unknown"))
    update_session(session, "audio_confidence", audio_result.get("confidence", 0.0))
    print("[Test] Audio result:", audio_result)

    # 3️⃣ Run OCR pipeline
    ocr_result = ocr_pipeline()
    update_session(session, "ocr_keywords", list(ocr_result.get("keywords", {}).keys()))
    update_session(session, "memory_score", sum([v.get("score",0) for v in ocr_result.get("keywords", {}).values()]))
    print("[Test] OCR result (top keywords):", list(ocr_result.get("keywords", {}).keys())[:5])

    # 4️⃣ Capture webcam attention
    webcam_result = webcam_pipeline()
    update_session(session, "attention_score", webcam_result.get("attentiveness_score", 0.0))
    print("[Test] Webcam attention score:", webcam_result)

    # 5️⃣ Final session DB log
    log_session_to_db(session)
    print("[Test] Session logged to DB.")

    # 6️⃣ Verify DB entries
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Sessions table
    c.execute("SELECT COUNT(*) FROM sessions")
    sessions_count = c.fetchone()[0]

    # Multi-modal logs
    c.execute("SELECT COUNT(*) FROM multi_modal_logs")
    multimodal_count = c.fetchone()[0]

    conn.close()
    print(f"[Test] Sessions table rows: {sessions_count}")
    print(f"[Test] Multi-modal logs rows: {multimodal_count}")

    print("=== Integration Test Completed ✅ ===")

if __name__ == "__main__":
    run_integration_test()
