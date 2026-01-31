# master_pipeline.py
"""
Master Multi-Modal Session Pipeline (IEEE-Ready)
------------------------------------------------
- Integrates Audio, OCR, Webcam, and Session Manager
- Updates central session object continuously
- Logs events to multi-modal DB and sessions table
- Aggregates attention, keywords, and concepts per session
"""

import time
from typing import Dict, Any
from core.session_manager import create_session, update_session, log_session_to_db
from core.audio_module import audio_pipeline
from core.ocr_module import ocr_pipeline
from core.webcam_module import webcam_pipeline
import logging
import os

# -----------------------------
# Logger setup
# -----------------------------
if not os.path.exists("logs"):
    os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/master_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -----------------------------
# Master session pipeline
# -----------------------------
def run_session(interval_sec: float = 5.0, max_iterations: int = 10) -> Dict[str, Any]:
    session = create_session()
    attention_history = []
    keywords_history = []

    for i in range(max_iterations):
        logging.info(f"[MasterPipeline] Iteration {i+1}/{max_iterations}")

        # --- Audio ---
        audio_result = audio_pipeline()
        update_session(session, "audio_label", audio_result.get("audio_label", "silence"))
        update_session(session, "audio_confidence", audio_result.get("confidence", 0.0))

        # --- OCR ---
        ocr_result = ocr_pipeline()
        update_session(session, "ocr_keywords", list(ocr_result.get("keywords", {}).keys()))
        keywords_history.extend(list(ocr_result.get("keywords", {}).keys()))

        # --- Webcam ---
        webcam_result = webcam_pipeline(num_frames=5)
        attention_score = webcam_result.get("attentiveness_score", 0.0)
        update_session(session, "attention_score", attention_score)
        attention_history.append(attention_score)

        # --- Aggregate / Wait ---
        logging.info(
            f"Audio: {audio_result.get('audio_label')} | "
            f"Attention: {attention_score:.2f} | "
            f"Keywords: {list(ocr_result.get('keywords', {}).keys())}"
        )

        time.sleep(interval_sec)

    # --- Final Aggregation ---
    avg_attention = sum(attention_history) / len(attention_history) if attention_history else 0.0
    top_keywords = sorted(set(keywords_history), key=lambda k: keywords_history.count(k), reverse=True)

    update_session(session, "attention_score", avg_attention)
    update_session(session, "ocr_keywords", top_keywords)

    # --- Final DB log ---
    log_session_to_db(session)
    logging.info("[MasterPipeline] Session completed and logged.")

    return {
        "session_summary": session,
        "avg_attention": avg_attention,
        "top_keywords": top_keywords
    }

# -----------------------------
# Self-test / Demo
# -----------------------------
if __name__ == "__main__":
    summary = run_session(interval_sec=3, max_iterations=5)
    print("Session Summary:")
    print("Avg Attention:", summary["avg_attention"])
    print("Top Keywords:", summary["top_keywords"])
