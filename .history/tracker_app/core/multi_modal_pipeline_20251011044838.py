"""
Real-Time Multi-Modal Stream Pipeline (IEEE-Ready)
---------------------------------------------------
- Continuously captures audio, webcam, and OCR
- Logs all events to multi-modal database
- Safe failover if any module fails
"""

import time
import logging
from typing import Dict, Any

from core.audio_module import audio_pipeline
from core.ocr_module import ocr_pipeline
from core.webcam_module import webcam_pipeline
from core.db_module import log_multi_modal_event

# -----------------------------
# LOGGER SETUP
# -----------------------------
logging.basicConfig(
    filename="logs/multi_modal_stream.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -----------------------------
# Streaming pipeline
# -----------------------------
def multi_modal_stream(interval_sec: int = 5, max_iterations: int = 10):
    """
    Run multi-modal pipeline continuously.
    - interval_sec: time between iterations
    - max_iterations: number of iterations before stopping
    """
    for i in range(max_iterations):
        logging.info(f"[Stream] Iteration {i+1}/{max_iterations} starting...")
        result: Dict[str, Any] = {}

        # -------- Audio --------
        try:
            audio_res = audio_pipeline()
            result["audio"] = audio_res
            log_multi_modal_event(
                window_title=f"Audio Classification: {audio_res.get('audio_label')}",
                audio_label=audio_res.get("audio_label"),
                intent_label=None,
                intent_confidence=audio_res.get("confidence", 0.0),
                attention_score=None,
                memory_score=None,
                source_module="AudioModule"
            )
        except Exception as e:
            logging.error(f"[Stream] Audio module failed: {e}")

        # -------- OCR --------
        try:
            ocr_res = ocr_pipeline()
            result["ocr"] = ocr_res
            log_multi_modal_event(
                window_title="OCR Extraction",
                ocr_keywords=",".join(ocr_res.get("keywords", {}).keys()),
                attention_score=None,
                audio_label=None,
                intent_label=None,
                intent_confidence=None,
                memory_score=None,
                source_module="OCRModule"
            )
        except Exception as e:
            logging.error(f"[Stream] OCR module failed: {e}")

        # -------- Webcam --------
        try:
            webcam_res = webcam_pipeline()
            result["webcam"] = webcam_res
            log_multi_modal_event(
                window_title="Webcam Attention",
                attention_score=webcam_res.get("attentiveness_score", 0.0),
                audio_label=None,
                intent_label=None,
                intent_confidence=None,
                memory_score=None,
                source_module="WebcamModule"
            )
        except Exception as e:
            logging.error(f"[Stream] Webcam module failed: {e}")

        logging.info(f"[Stream] Iteration {i+1} completed: {result}")
        print(f"Iteration {i+1} completed. Result keys: {list(result.keys())}")

        # Wait before next iteration
        time.sleep(interval_sec)

# -----------------------------
# SELF-TEST / DEMO
# -----------------------------
if __name__ == "__main__":
    multi_modal_stream(interval_sec=5, max_iterations=5)
