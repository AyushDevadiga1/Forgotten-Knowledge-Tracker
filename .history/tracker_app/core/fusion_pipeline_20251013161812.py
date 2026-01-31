# core/fusion_pipeline.py
"""
Unified Multi-Modal Fusion Pipeline (IEEE-Ready v3)
---------------------------------------------------
- Async orchestration of Audio, OCR, Webcam
- Integrates Intent, Memory Model, Knowledge Graph, and Reminders
- Structured logging & session aggregation
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from core.audio_module import audio_pipeline
from core.ocr_module import ocr_pipeline
from core.webcam_module import webcam_pipeline
from core.intent_module import predict_intent
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve
from core.knowledge_graph import add_edges, sync_db_to_graph, get_graph
from core.reminders import check_reminders
from core.db_module import log_multi_modal_event, init_multi_modal_db

# -----------------------------
# Logger Setup
# -----------------------------
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/fusion_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -----------------------------
# Initialize DB
# -----------------------------
init_multi_modal_db()

# -----------------------------
# Async Fusion Pipeline
# -----------------------------
async def run_fusion_pipeline(interval_sec: float = 5.0, max_iterations: int = 10) -> Any:
    G = get_graph()

    for i in range(max_iterations):
        iteration_result: Dict[str, Any] = {}
        timestamp = datetime.now()

        # Run modalities concurrently
        audio_task = asyncio.to_thread(audio_pipeline)
        ocr_task = asyncio.create_task(ocr_pipeline())
        webcam_task = asyncio.create_task(webcam_pipeline(num_frames=5))

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
            attention_score = webcam_res.get("attentiveness_score", 50.0)
            webcam_active = webcam_res.get("user_present", True)
            iteration_result["webcam"] = webcam_res

        # --- Intent ---
        intent_res = predict_intent(
            ocr_keywords=ocr_keywords,
            audio_label=audio_label,
            attention_score=attention_score,
            interaction_rate=0.0,
            use_webcam=True
        )
        iteration_result["intent"] = intent_res
        intent_label = intent_res.get("intent_label", "unknown")
        intent_conf = intent_res.get("confidence", 0.0)

        # --- Memory Score ---
        memory_score = compute_memory_score(
            last_review_time=timestamp,
            lambda_val=0.1,
            intent_conf=intent_conf,
            attention_score=attention_score,
            audio_conf=audio_conf
        )
        next_review = schedule_next_review(timestamp, memory_score, lambda_val=0.1)
        iteration_result["memory_score"] = memory_score

        for kw in ocr_keywords:
            log_forgetting_curve(kw, timestamp)

        # --- Knowledge Graph Update ---
        add_edges({kw:1 for kw in ocr_keywords}, audio_label, intent_label, G)
        sync_db_to_graph()

        # --- Reminders ---
        check_reminders(attention_score=attention_score, interaction_rate=0.0, webcam_active=webcam_active)

        # --- Logging ---
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
        logging.info(f"[Fusion] Iteration {i+1} completed: {iteration_result}")
        print(f"Iteration {i+1} completed: intent={intent_label}, memory={memory_score:.2f}")

        await asyncio.sleep(interval_sec)

    return G


# -----------------------------
# Self-Test / Demo
# -----------------------------
if __name__ == "__main__":
    print("🚀 Running Unified Fusion Pipeline asynchronously...")
    asyncio.run(run_fusion_pipeline(interval_sec=3, max_iterations=5))
    G = get_graph()
    print(f"✅ Fusion Pipeline finished. KG nodes: {len(G.nodes)}, edges: {len(G.edges)}")
