#core/multi_modal_pipeline.py
"""
Unified Multi-Modal Pipeline (IEEE-Ready)
------------------------------------------
- Audio capture & classification
- Intent prediction using OCR/audio/interaction/attention
- Memory score computation & forgetting curve logging
- Spaced-review reminders
- Centralized DB logging for all events
"""

from datetime import datetime
from typing import Dict, Any
from core.audio_module import audio_pipeline
from core.intent_module import predict_intent
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve
from core.reminders import check_reminders
from core.db_module import log_multi_modal_event
from core.session_manager import create_session, update_session

# -----------------------------
# Central Pipeline Object
# -----------------------------
def process_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes one session cycle: Audio -> Intent -> Memory -> DB log
    Returns updated session dict
    """
    try:
        # -----------------------------
        # Step 1: Audio
        # -----------------------------
        audio_result = audio_pipeline()
        session["audio_label"] = audio_result["audio_label"]
        session["audio_confidence"] = audio_result["confidence"]

        # -----------------------------
        # Step 2: Intent
        # -----------------------------
        intent_result = predict_intent(
            ocr_keywords=session.get("ocr_keywords", []),
            audio_label=session["audio_label"],
            attention_score=session.get("attention_score", 50),
            interaction_rate=session.get("interaction_rate", 0),
            use_webcam=session.get("use_webcam", False)
        )
        session["intent_label"] = intent_result["intent_label"]
        session["intent_confidence"] = intent_result["confidence"]

        # -----------------------------
        # Step 3: Memory Score
        # -----------------------------
        last_review_time = session.get("last_review", datetime.now())
        memory_score = compute_memory_score(
            last_review_time=last_review_time,
            lambda_val=0.1,
            intent_conf=session["intent_confidence"],
            attention_score=session.get("attention_score", 50),
            audio_conf=session.get("audio_confidence", 1.0)
        )
        session["memory_score"] = memory_score
        session["next_review"] = schedule_next_review(last_review_time, memory_score, lambda_val=0.1)

        # Log forgetting curve to DB
        log_forgetting_curve(
            concept=session.get("window_title", "Unknown"),
            last_seen_time=last_review_time
        )

        # -----------------------------
        # Step 4: Central DB Logging
        # -----------------------------
        log_multi_modal_event(
            window_title=session.get("window_title", "Unknown"),
            ocr_keywords=", ".join(session.get("ocr_keywords", [])),
            audio_label=session["audio_label"],
            attention_score=session.get("attention_score", 50),
            interaction_rate=session.get("interaction_rate", 0),
            intent_label=session["intent_label"],
            intent_confidence=session["intent_confidence"],
            memory_score=session["memory_score"],
            source_module="UnifiedPipeline"
        )

        # -----------------------------
        # Update last_review
        # -----------------------------
        session["last_review"] = datetime.now()

    except Exception as e:
        print(f"[MultiModalPipeline] Error processing session: {e}")

    return session

# -----------------------------
# SELF-TEST
# -----------------------------
if __name__ == "__main__":
    # Create a sample session
    session = create_session()
    session["window_title"] = "Photosynthesis"
    session["ocr_keywords"] = ["chlorophyll", "light reaction"]
    session["attention_score"] = 80
    session["interaction_rate"] = 10
    session["use_webcam"] = True

    # Process session
    updated_session = process_session(session)
    print("✅ Updated Session Data:")
    for k, v in updated_session.items():
        print(f"{k}: {v}")

    # Trigger reminders
    sent_count = check_reminders()
    print(f"✅ Reminders sent: {sent_count}")
