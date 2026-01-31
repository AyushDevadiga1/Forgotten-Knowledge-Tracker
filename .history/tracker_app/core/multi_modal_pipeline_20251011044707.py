"""
Multi-Modal Tracker Pipeline (IEEE-Ready)
-----------------------------------------
Integrates:
- Audio (AudioModule)
- OCR/Text (OCRModule)
- Webcam attention (WebcamModule)

Logs all events safely to the multi-modal DB.
"""

from typing import Dict, Any
import logging
from datetime import datetime

from core.audio_module import audio_pipeline
from core.ocr_module import ocr_pipeline
from core.webcam_module import webcam_pipeline
from core.db_module import log_multi_modal_event

# -----------------------------
# LOGGER SETUP
# -----------------------------
logging.basicConfig(
    filename="logs/multi_modal_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -----------------------------
# Multi-modal aggregation
# -----------------------------
def run_multi_modal_pipeline() -> Dict[str, Any]:
    """
    Runs audio, OCR, and webcam pipelines in a safe, integrated manner.
    Returns combined structured result.
    """
    result: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "audio": {},
        "ocr": {},
        "webcam": {}
    }

    # -----------------------------
    # 1️⃣ Audio Module
    # -----------------------------
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
        logging.error(f"[Pipeline] Audio module failed: {e}")

    # -----------------------------
    # 2️⃣ OCR Module
    # -----------------------------
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
        logging.error(f"[Pipeline] OCR module failed: {e}")

    # -----------------------------
    # 3️⃣ Webcam Module
    # -----------------------------
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
        logging.error(f"[Pipeline] Webcam module failed: {e}")

    logging.info(f"[Pipeline] Multi-modal pipeline run completed.")
    return result

# -----------------------------
# SELF-TEST / DEMO
# -----------------------------
if __name__ == "__main__":
    final_res = run_multi_modal_pipeline()
    print("=== Multi-Modal Pipeline Result ===")
    print(final_res)
