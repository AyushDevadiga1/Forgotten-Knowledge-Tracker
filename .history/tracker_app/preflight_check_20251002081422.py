# preflight_strict_stress_test.py
import numpy as np
from core import intent_module
from core.db_ import init_db, init_multi_modal_db
import sqlite3
from config import DB_PATH

# -------------------------------
# Initialize databases
# -------------------------------
init_db()
init_multi_modal_db()
print("Databases initialized.")

# -------------------------------
# Test configurations
# -------------------------------
audio_labels = ["speech", "music", "silence", "unknown"]
ocr_counts = [0, 1, 5, 50, 1000]  # extreme OCR cases
attention_scores = [0, 25, 50, 75, 100]  # attention extremes
interaction_rates = [0, 1, 5, 10, 100]  # interaction extremes

# -------------------------------
# Stress Test
# -------------------------------
def run_stress_test():
    failures = []
    test_num = 1

    for ocr_count in ocr_counts:
        for audio in audio_labels:
            for att in attention_scores:
                for interact in interaction_rates:
                    ocr_keywords = ["kw"] * ocr_count
                    input_data = {
                        "ocr_keywords": ocr_keywords,
                        "audio_label": audio,
                        "attention_score": att,
                        "interaction_rate": interact
                    }

                    # -------------------------------
                    # Feature extraction
                    # -------------------------------
                    features = intent_module.extract_features(
                        ocr_keywords, audio, att, interact
                    )
                    if features.shape != (1, 4):
                        failures.append(f"Feature shape failed: {features.shape} | {input_data}")

                    # -------------------------------
                    # Intent prediction
                    # -------------------------------
                    intent_result = intent_module.predict_intent(
                        ocr_keywords, audio, att, interact
                    )
                    if "intent_label" not in intent_result or "confidence" not in intent_result:
                        failures.append(f"Intent prediction failed: {intent_result} | {input_data}")

                    # -------------------------------
                    # Database logging test
                    # -------------------------------
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute('''
                            INSERT INTO multi_modal_logs
                            (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            "2025-10-02 10:00:00",
                            "TestWindow",
                            str({kw: {"score": 0.5, "count": 1} for kw in ocr_keywords}),
                            audio,
                            att,
                            interact,
                            intent_result["intent_label"],
                            intent_result["confidence"]
                        ))
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        failures.append(f"DB logging failed: {e} | {input_data}")

                    test_num += 1

    print(f"Stress test completed: {test_num} combinations tested.")
    if failures:
        print(f"Failures detected: {len(failures)}")
        for f in failures:
            print(f)
    else:
        print("All tests passed successfully!")

# -------------------------------
# Run the stress test
# -------------------------------
if __name__ == "__main__":
    run_stress_test()
