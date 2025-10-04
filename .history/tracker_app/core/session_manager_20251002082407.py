# stress_test_full.py
import itertools
import sqlite3
from datetime import datetime
from core.intent_module import predict_intent
from core.session_manager import log_session
from config import DB_PATH

# ------------------------------
# Test parameter sets
# ------------------------------
windows = ["Visual Studio Code", "Google Chrome", "TestWindow", None, "特殊窗口"]
audio_labels = ["speech", "music", "silence", "unknown"]
interaction_rates = [0, 1, 3, 5, 10, 50, 100]
ocr_keywords_list = [
    [],
    ["python", "code"],
    ["physics", "chemistry", "biology", "math", "OCI", "debug"],
    ["特殊字符", "emoji😊"],
]

# ------------------------------
# Database helper
# ------------------------------
def fetch_db_summary():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    print("\n=== Sessions Table Summary ===")
    for row in c.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 5"):
        print(row)
    print("\n=== Multi-Modal Logs Table Summary ===")
    for row in c.execute("SELECT * FROM multi_modal_logs ORDER BY id DESC LIMIT 5"):
        print(row)
    conn.close()

# ------------------------------
# Run stress tests
# ------------------------------
print("=== FULL STRESS TEST START ===")
count = 0
for window, audio, interaction, ocr in itertools.product(
    windows, audio_labels, interaction_rates, ocr_keywords_list
):
    count += 1
    try:
        intent_result = predict_intent(
            ocr_keywords=ocr,
            audio_label=audio,
            attention_score=50,  # fixed for testing
            interaction_rate=interaction,
            use_webcam=False
        )
        # Log session safely
        log_session(
            window_title=window or "Unknown",
            interaction_rate=interaction,
            audio_label=audio,
            intent_label=intent_result["intent_label"],
            intent_confidence=intent_result["confidence"]
        )

        print(
            f"Test {count}: Window='{window}', Audio='{audio}', "
            f"Interaction={interaction}, OCR={ocr}\n"
            f"  -> Intent='{intent_result['intent_label']}', "
            f"Confidence={intent_result['confidence']:.3f}"
        )
    except Exception as e:
        print(f"Test {count} FAILED: {e}")

print(f"\n=== FULL STRESS TEST COMPLETED ({count} combinations tested) ===")

# Fetch latest DB entries for verification
fetch_db_summary()
