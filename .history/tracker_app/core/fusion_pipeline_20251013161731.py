#core/fusion_pipeline.py
"""
Unified Multi-Modal Fusion Pipeline (IEEE-Ready)
------------------------------------------------
- Combines Audio, OCR, Webcam capture
- Feeds into Intent Module, Memory Model, Knowledge Graph, and Reminders
- Centralized logging and session aggregation
"""

import time
import logging
import os 
from datetime import datetimea# fusion_pipeline.py
"""
Unified Multi-Modal Fusion Pipeline (IEEE-Ready v2)
---------------------------------------------------
- Combines Audio, OCR, Webcam capture
- Feeds into Intent Module, Memory Model, Knowledge Graph, and Reminders
- Centralized logging and session aggregation
- Async-ready for OCR/Webcam pipelines
"""

import time
import logging
import os
import asyncio
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

# ==============================
# Logger Setup
# ==============================
if not os.path.exists("logs"):
    os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/fusion_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ==============================
# Initialize DB
# ==============================
init_multi_modal_db()

# ==============================
# Fusion Pipeline (async-ready)
# ==============================
async def run_fusion_pipeline(interval_sec: float = 5.0, max_iterations: int = 10):
    """
    Runs unified multi-modal pipeline asynchronously.
    - Captures modalities, predicts intent, computes memory scores
    - Updates knowledge graph and triggers reminders
    """
    G = get_graph()

    for i in range(max_iterations):
        iteration_result: Dict[str, Any] = {}
        timestamp = datetime.now()

        # -----------------------------
        # Audio
        # -----------------------------
        try:
            audio_res = audio_pipeline()
            audio_label = audio_res.get("audio_label", "silence")
            audio_conf = audio_res.get("confidence", 0.0)
            iteration_result["audio"] = audio_res
        except Exception as e:
            logging.error(f"[Fusion] Audio module failed: {e}")
            audio_label, audio_conf = "silence", 0.0

        # -----------------------------
        # OCR
        # -----------------------------
        try:
            ocr_res = await ocr_pipeline() if asyncio.iscoroutinefunction(ocr_pipeline) else ocr_pipeline()
            ocr_keywords = list(ocr_res.get("keywords", {}).keys())
            iteration_result["ocr"] = ocr_res
        except Exception as e:
            logging.error(f"[Fusion] OCR module failed: {e}")
            ocr_keywords = []

        # -----------------------------
        # Webcam
        # -----------------------------
        try:
            webcam_res = await webcam_pipeline(num_frames=5) if asyncio.iscoroutinefunction(webcam_pipeline) else webcam_pipeline(num_frames=5)
            attention_score = webcam_res.get("attentiveness_score", 0.0)
            webcam_active = webcam_res.get("user_present", True)
            iteration_result["webcam"] = webcam_res
        except Exception as e:
            logging.error(f"[Fusion] Webcam module failed: {e}")
            attention_score = 50.0
            webcam_active = True

        # -----------------------------
        # Intent Prediction
        # -----------------------------
        try:
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
        except Exception as e:
            logging.error(f"[Fusion] Intent prediction failed: {e}")
            intent_label, intent_conf = "unknown", 0.0

        # -----------------------------
        # Memory Score
        # -----------------------------
        try:
            memory_score = compute_memory_score(
                last_review_time=timestamp,
                lambda_val=0.1,
                intent_conf=intent_conf,
                attention_score=attention_score,
                audio_conf=audio_conf
            )
            iteration_result["memory_score"] = memory_score
            next_review = schedule_next_review(timestamp, memory_score, lambda_val=0.1)
        except Exception as e:
            logging.error(f"[Fusion] Memory model failed: {e}")
            memory_score = 0.0

        # Log forgetting curve
        for kw in ocr_keywords:
            try:
                log_forgetting_curve(kw, timestamp)
            except Exception:
                pass

        # -----------------------------
        # Knowledge Graph Update
        # -----------------------------
        try:
            add_edges(
                ocr_keywords={kw: 1 for kw in ocr_keywords},
                audio_label=audio_label,
                intent_label=intent_label,
                G=G
            )
            sync_db_to_graph()
        except Exception as e:
            logging.error(f"[Fusion] KG update failed: {e}")

        # -----------------------------
        # Reminder Check
        # -----------------------------
        try:
            check_reminders(attention_score=attention_score, interaction_rate=0.0, webcam_active=webcam_active)
        except Exception as e:
            logging.error(f"[Fusion] Reminder check failed: {e}")

        # -----------------------------
        # Iteration Logging
        # -----------------------------
        try:
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
        except Exception:
            pass

        logging.info(f"[Fusion] Iteration {i+1} completed: {iteration_result}")
        print(f"Iteration {i+1} completed: intent={intent_label}, memory={memory_score:.2f}")

        await asyncio.sleep(interval_sec)

    return G

# ==============================
# Self-Test / Demo
# ==============================
if __name__ == "__main__":
    print("🚀 Running Unified Fusion Pipeline asynchronously...")
    asyncio.run(run_fusion_pipeline(interval_sec=3, max_iterations=5))
    G = get_graph()
    print(f"✅ Fusion Pipeline finished. KG nodes: {len(G.nodes)}, edges: {len(G.edges)}")

from typing import Dict, Any, List
from core.audio_module import audio_pipeline
from core.ocr_module import ocr_pipeline
from core.webcam_module import webcam_pipeline
from core.intent_module import predict_intent
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve
from core.knowledge_graph import add_edges, sync_db_to_graph, get_graph
from core.reminders import check_reminders
from core.db_module import log_multi_modal_event, init_multi_modal_db

# ==============================
# Logger Setup
# ==============================
if not os.path.exists("logs"):
    os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/fusion_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ==============================
# Initialize DB
# ==============================
init_multi_modal_db()

# ==============================
# Fusion Pipeline
# ==============================
def run_fusion_pipeline(interval_sec: float = 5.0, max_iterations: int = 10):
    """
    Runs unified multi-modal pipeline.
    - Captures modalities, predicts intent, computes memory scores
    - Updates knowledge graph and triggers reminders
    """
    G = get_graph()

    for i in range(max_iterations):
        iteration_result: Dict[str, Any] = {}
        timestamp = datetime.now()

        # -----------------------------
        # Audio
        # -----------------------------
        try:
            audio_res = audio_pipeline()
            audio_label = audio_res.get("audio_label", "silence")
            audio_conf = audio_res.get("confidence", 0.0)
            iteration_result["audio"] = audio_res
        except Exception as e:
            logging.error(f"[Fusion] Audio module failed: {e}")
            audio_label, audio_conf = "silence", 0.0

        # -----------------------------
        # OCR
        # -----------------------------
        try:
            ocr_res = ocr_pipeline()
            ocr_keywords = list(ocr_res.get("keywords", {}).keys())
            iteration_result["ocr"] = ocr_res
        except Exception as e:
            logging.error(f"[Fusion] OCR module failed: {e}")
            ocr_keywords = []

        # -----------------------------
        # Webcam
        # -----------------------------
        try:
            webcam_res = webcam_pipeline(num_frames=5)
            attention_score = webcam_res.get("attentiveness_score", 0.0)
            iteration_result["webcam"] = webcam_res
        except Exception as e:
            logging.error(f"[Fusion] Webcam module failed: {e}")
            attention_score = 50.0

        # -----------------------------
        # Intent Prediction
        # -----------------------------
        intent_res = predict_intent(
            ocr_keywords=ocr_keywords,
            audio_label=audio_label,
            attention_score=attention_score,
            interaction_rate=0.0,  # optionally integrate mouse/keyboard later
            use_webcam=True
        )
        iteration_result["intent"] = intent_res
        intent_label = intent_res.get("intent_label", "unknown")
        intent_conf = intent_res.get("confidence", 0.0)

        # -----------------------------
        # Memory Score
        # -----------------------------
        memory_score = compute_memory_score(
            last_review_time=timestamp,
            lambda_val=0.1,
            intent_conf=intent_conf,
            attention_score=attention_score,
            audio_conf=audio_conf
        )
        iteration_result["memory_score"] = memory_score
        next_review = schedule_next_review(timestamp, memory_score, lambda_val=0.1)

        # Log forgetting curve
        for kw in ocr_keywords:
            log_forgetting_curve(kw, timestamp)

        # -----------------------------
        # Knowledge Graph Update
        # -----------------------------
        add_edges(
            ocr_keywords={kw: 1 for kw in ocr_keywords},
            audio_label=audio_label,
            intent_label=intent_label,
            G=G
        )
        sync_db_to_graph()  # ensure DB concepts sync

        # -----------------------------
        # Reminder Check
        # -----------------------------
        check_reminders()

        # -----------------------------
        # Iteration Logging
        # -----------------------------
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

        # -----------------------------
        # Wait for next iteration
        # -----------------------------
        time.sleep(interval_sec)

    return G

# ==============================
# Self-Test / Demo
# ==============================
if __name__ == "__main__":
    print("🚀 Running Unified Fusion Pipeline...")
    G = run_fusion_pipeline(interval_sec=3, max_iterations=5)
    print(f"✅ Fusion Pipeline finished. KG nodes: {len(G.nodes)}, edges: {len(G.edges)}")
