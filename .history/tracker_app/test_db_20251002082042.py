# core/stress_test_tracker.py
import random
from datetime import datetime
from core.intent_module import predict_intent
from core.session_manager import log_session
from config import DB_PATH
import sqlite3

# Simulated OCR keyword sets
ocr_samples = [
    [],  # empty
    ["python", "code"],  # small normal
    ["physics", "chemistry", "biology", "math", "OCI", "debug"],  # many keywords
    ["特殊字符", "emoji😊"],  # unusual characters
]

# Audio options
audio_labels = ["speech", "music", "silence", "unknown"]

# Attention scores
attention_scores = [0, 50, 100]

# Interaction rates
interaction_rates = [0, 3, 10, 50, 100]

# Window/app names
window_titles = ["Visual Studio Code", "Google Chrome", "TestWindow", None, "特殊窗口"]

# Number of stress test iterations
NUM_TESTS = 50

print("=== STRESS TEST START ===")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

for i in range(NUM_TESTS):
    ocr = random.choice(ocr_samples)
    audio = random.choice(audio_labels)
    att = random.choice(attention_scores)
    interaction = random.choice(interaction_rates)
    window = random.choice(window_titles)
    app_name = window if window else "Unknown App"

    # Predict intent
    result = predict_intent(ocr, audio, att, interaction, use_webcam=False)

    # Log session
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_session(
        start_ts=timestamp,
        end_ts=timestamp,
        app_name=app_name,
        window_title=window,
        interaction_rate=interaction,
        audio_label=audio,
        intent_label=result["intent_label"],
        intent_confidence=result["confidence"]
    )

    print(f"Test {i+1}: Window='{window}', Audio='{audio}', Interaction={interaction}, OCR={ocr}")
    print(f"  -> Intent='{result['intent_label']}', Confidence={result['confidence']:.3f}")

conn.close()
print("=== STRESS TEST COMPLETED ===")
