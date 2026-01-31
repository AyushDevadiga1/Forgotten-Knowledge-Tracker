# ==========================================================
# core/fusion_pipeline_v4.py | IEEE v4 Multi-Modal Fusion
# ==========================================================
"""
Unified Multi-Modal Fusion Pipeline (IEEE v4)
---------------------------------------------
- Async orchestration of Audio, OCR, Webcam
- Integrates Intent v4, Memory Model, Knowledge Graph, Reminders
- Temporal smoothing, dynamic config, session tracking
- Structured logging & DB integration
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

from config import TRACK_INTERVAL
from core.audio_module import AudioModule
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
    filename="logs/fusion_pipeline_v4.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("FusionPipelineV4")

# ==========================================================
# Initialize DB
# ==========================================================
init_multi_modal_db()

# ==========================================================
# Audio Module Instance
# ==========================================================
audio_module = AudioModule()
audio_module.start_async()  # background recording loop

# ==========================================================
# Async Fusion Pipeline
# ==========================================================
async def run_fusion_pipeline_v4(interval_sec: float = TRACK_INTERVAL, max_iterations: int = 10) -> Dict[str, Any]:
    G = get_graph()
    session = create_session()

    for i in range(max_iterations):
        iteration_result: Dict[str, Any] = {}
        timestamp = datetime.now()

        # Run modalities concurrently
        audio_task = asyncio.create_task(audio_module.async_pipeline())
        ocr_task = asyncio.create_task(ocr_pipeline())
        webcam_task = asyncio.create_task(webcam_pipeline())

        audio_res, ocr_res, webcam_res = await asyncio.gather(audio_task, ocr_task, webcam_task, return_exceptions=True)

        # --- Audio ---
        audio_label, audio_conf = "silence", 0.0
        if isinstance(audio_res, dict):
            audio_label = audio_res.get("audio_label", "silence")
            audio_conf = audio_res.get("confidence", 0.0)
            iteration_result["audio"] = audio_res

        # --- OCR ---
        ocr_keywords: List[str] = []
        if isinstance(ocr_res, dict):
            ocr_keywords = list(ocr_res.get("keywords", {}).keys())
            iteration_result["ocr"] = ocr_res

        # --- Webcam ---
        attention_score, webcam_active = 50.0, True
        if isinstance(webcam_res, dict):
            attention_score = webcam_res.get("confidence", 50.0) * 100.0 / 1.0  # scale to 0-100
            webcam_active = webcam_res.get("attentive", True)
            iteration_result["webcam"] = webcam_res

        # --- Intent v4 ---
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

        log_multi_modal_event(
            window_title=f"Fusion Iteration {i+1}",
            ocr_keywords=",".join(ocr_keywords),
            audio_label=audio_label,
            attention_score=attention_score,
            intent_label=intent_label,
            intent_confidence=intent_conf,
            memory_score=memory_score,
            source_module="FusionPipelineV4"
        )

        logger.info(f"[Fusion v4] Iteration {i+1} completed: {iteration_result}")
        print(f"Iteration {i+1} completed: intent={intent_label}, memory={memory_score:.2f}")

        await asyncio.sleep(interval_sec)

    return iteration_result

# ==========================================================
# Self-Test / Demo
# ==========================================================
if __name__ == "__main__":
    print("🚀 Running Unified Fusion Pipeline v4 asynchronously...")
    asyncio.run(run_fusion_pipeline_v4(interval_sec=3, max_iterations=5))
    G = get_graph()
    print(f"✅ Fusion Pipeline v4 finished. KG nodes: {len(G.nodes)}, edges: {len(G.edges)}")
