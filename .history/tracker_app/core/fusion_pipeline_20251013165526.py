# ==========================================================
# core/fusion_pipeline.py | IEEE v4 Fault-Tolerant Multi-Modal
# ==========================================================
"""
Unified Multi-Modal Fusion Pipeline (Fault-Tolerant v4)
-------------------------------------------------------
- Async orchestration of Audio, OCR, Webcam
- Handles module failures gracefully (defaults & safe wrappers)
- Integrates Intent, Memory Model, Knowledge Graph, and Reminders
- Dynamic config usage & session tracking
- Structured logging & session aggregation
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

from config import TRACK_INTERVAL
from core.audio_module import audio_module
from core.ocr_module import ocr_pipeline
from core.webcam_module import webcam_pipeline
from core.intent_module import predict_intent
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve
from core.knowledge_graph import add_multimodal_edges, sync_db_to_graph, get_graph
from core.reminders import check_reminders
from core.db_module import log_multi_modal_event, init_multi_modal_db
from core.session_manager import create_session, update_session, log_session_to_db

# ==========================================================
# Logger Setup
# ==========================================================
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/fusion_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("FusionPipeline")

# ==========================================================
# Initialize DB
# ==========================================================
init_multi_modal_db()

# ==========================================================
# Fault-Tolerant Module Wrappers
# ==========================================================
async def safe_audio() -> Dict[str, Any]:
    try:
        return await audio_module.async_pipeline()
    except Exception as e:
        logger.error(f"Audio module failed: {e}")
        return {"audio_label": "silence", "confidence": 0.0, "attentive": False}

async def safe_ocr() -> Dict[str, Any]:
    try:
        return await ocr_pipeline()
    except Exception as e:
        logger.error(f"OCR module failed: {e}")
        return {"keywords": {}, "embedding_v2": [], "concepts_v2": [], "raw_text": ""}

async def safe_webcam() -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(webcam_pipeline)
    except Exception as e:
        logger.error(f"Webcam module failed: {e}")
        return {"attentive": False, "confidence": 0.0, "frame": None}

# ==========================================================
# Async Fusion Pipeline
# ==========================================================
async def run_fusion_pipeline(interval_sec: float = TRACK_INTERVAL, max_iterations: int = 10) -> Dict[str, Any]:
    G = get_graph()
    session = create_session()

    for i in range(max_iterations):
        iteration_result: Dict[str, Any] = {}
        timestamp = datetime.now()

        # Run modalities concurrently (fault-tolerant)
        audio_task = asyncio.create_task(safe_audio())
        ocr_task = asyncio.create_task(safe_ocr())
        webcam_task = asyncio.create_task(safe_webcam())

        audio_res, ocr_res, webcam_res = await asyncio.gather(
            audio_task, ocr_task, webcam_task
        )

        # --- Audio ---
        audio_label = audio_res.get("audio_label", "silence")
        audio_conf = audio_res.get("confidence", 0.0)
        iteration_result["audio"] = audio_res

        # --- OCR ---
        ocr_keywords = list(ocr_res.get("keywords", {}).keys())
        iteration_result["ocr"] = ocr_res

        # --- Webcam ---
        attention_score = webcam_res.get("confidence", 50.0)
        webcam_active = webcam_res.get("attentive", True)
        iteration_result["webcam"] = webcam_res

        # --- Intent ---
        intent_res = await predict_intent(
            ocr_keywords=ocr_keywords,
            audio_label=audio_label,
            attention_score=attention_score,
            interaction_rate=0.0,
            use_webcam=True
        )
        intent_label = intent_res.get("intent_label", "unknown")
        intent_conf = intent_res.get("confidence", 0.0)
        iteration_result["intent"] = intent_res

        # --- Memory Score ---
        memory_score = compute_memory_score(
            last_review_time=timestamp,
            lambda_val=0.1,
            intent_conf=intent_conf,
            attention_score=attention_score,
            audio_conf=audio_conf,
            update_graph=True
        )
        next_review = schedule_next_review(timestamp, memory_score, lambda_val=0.1)
        iteration_result["memory_score"] = memory_score

        # Log forgetting curve for OCR keywords
        for kw in ocr_keywords:
            log_forgetting_curve(kw, timestamp)

        # --- Knowledge Graph Update ---
        add_multimodal_edges({kw: 1 for kw in ocr_keywords}, audio_label, intent_label)
        sync_db_to_graph()

        # --- Reminders ---
        check_reminders(attention_score=attention_score, interaction_rate=0.0, webcam_active=webcam_active)

        # --- Session Update & Logging ---
        update_session(session, "window_title", f"Fusion Iteration {i+1}")
        update_session(session, "ocr_keywords", ocr_keywords)
        update_session(session, "audio_label", audio_label)
        update_session(session, "attention_score", attention_score)
        update_session(session, "intent_label", intent_label)
        update_session(session, "intent_confidence", intent_conf)
        update_session(session, "memory_score", memory_score)
        update_session(session, "next_review", next_review)
        log_session_to_db(session)

        # Multi-modal event log
        log_multi_modal_event(
            window_title=f"Fusion Iteration {i+1}",
            ocr_keywords=",".join(ocr_keywords),
            audio_label=audio_label,
            attention_score=attention_score,
            intent_label=intent_label,
            intent_confidence=intent_conf,
            memory_score=memory_score,
            source_module="FusionPipeline"
        )

        logger.info(f"[Fusion] Iteration {i+1} completed: {iteration_result}")
        print(f"Iteration {i+1} completed: intent={intent_label}, memory={memory_score:.2f}")

        await asyncio.sleep(interval_sec)

    return iteration_result

# ==========================================================
# Self-Test / Demo
# ==========================================================
if __name__ == "__main__":
    print("🚀 Running Fault-Tolerant Fusion Pipeline asynchronously...")
    asyncio.run(run_fusion_pipeline(interval_sec=3, max_iterations=5))
    G = get_graph()
    print(f"✅ Fusion Pipeline finished. KG nodes: {len(G.nodes)}, edges: {len(G.edges)}")
