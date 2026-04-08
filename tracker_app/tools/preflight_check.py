# tools/preflight_check.py — FKT 2.0 Phase 12 fix
# Updated: expects 6-feature vector from new intent module (was 4 in v1)

import numpy as np
from tracker_app.tracking import intent_module
from tracker_app.db.db_module import init_all_databases
from tracker_app.config import DB_PATH
import sqlite3

init_all_databases()
print("Databases initialised.")

audio_labels      = ["speech", "music", "silence", "unknown"]
ocr_counts        = [0, 1, 5, 50]
attention_scores  = [0, 25, 50, 75, 100]
interaction_rates = [0, 1, 5, 10, 100]

EXPECTED_FEATURE_SHAPE = (1, 6)   # FKT 2.0: 6 features

def run_stress_test():
    failures = []
    test_num = 0

    for ocr_count in ocr_counts:
        for audio in audio_labels:
            for att in attention_scores:
                for interact in interaction_rates:
                    test_num += 1
                    ocr_keywords = {f"kw{i}": {"score": 0.5} for i in range(ocr_count)}

                    # 1. Feature extraction
                    features = intent_module.extract_features(
                        ocr_keywords, audio, att, interact
                    )
                    if features.shape != EXPECTED_FEATURE_SHAPE:
                        failures.append(
                            f"Feature shape {features.shape} != {EXPECTED_FEATURE_SHAPE} "
                            f"(ocr={ocr_count}, audio={audio}, att={att}, ir={interact})"
                        )

                    # 2. Intent prediction
                    result = intent_module.predict_intent(
                        ocr_keywords, audio, att, interact
                    )
                    if "intent_label" not in result or "confidence" not in result:
                        failures.append(f"Missing keys in result: {result}")

                    # 3. DB write
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        c    = conn.cursor()
                        c.execute("""
                            INSERT INTO multi_modal_logs
                            (timestamp, window_title, ocr_keywords, audio_label,
                             attention_score, interaction_rate, intent_label, intent_confidence)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            "2025-10-02T10:00:00", "TestWindow",
                            str(list(ocr_keywords.keys())),
                            audio, att, interact,
                            result["intent_label"], result["confidence"]
                        ))
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        failures.append(f"DB write failed: {e}")

    print(f"Stress test: {test_num} combinations tested.")
    if failures:
        print(f"Failures: {len(failures)}")
        for f in failures[:10]:
            print(f"  ✗ {f}")
    else:
        print("All tests passed!")

if __name__ == "__main__":
    run_stress_test()
