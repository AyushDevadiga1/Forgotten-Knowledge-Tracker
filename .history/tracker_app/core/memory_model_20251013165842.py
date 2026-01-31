    # ==========================================================
    # core/memory_model.py | FKT v4.0 Async & Multi-Modal
    # ==========================================================
    """
    Memory Model Module (IEEE-Ready v4.0)
    -------------------------------------
    - Computes memory scores using multi-modal signals & Ebbinghaus curve.
    - Supports batch updates, async logging, and integrates with knowledge graph.
    - Schedules next review adaptively.
    - Fully typed, logged, and IEEE 1016 / 12207 / 730 compliant.
    """

    import os
    import math
    import logging
    from datetime import datetime, timedelta
    from typing import Optional, List, Dict

    import numpy as np
    import asyncio

    from core.db_module import log_multi_modal_event_async, update_metric
    from core.knowledge_graph import get_graph
    from config import MEMORY_THRESHOLD, MIN_LAMBDA

    # ==========================================================
    # LOGGER SETUP
    # ==========================================================
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        handler = logging.FileHandler("logs/memory_model.log")
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(funcName)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # ==========================================================
    # SAFE EXEC DECORATOR
    # ==========================================================
    def safe_exec(func):
        """Wrap function with try/except logging."""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"{func.__name__} failed: {e}")
                return None
        return wrapper

    # ==========================================================
    # EBBINGHAUS FORGETTING CURVE
    # ==========================================================
    @safe_exec
    def forgetting_curve(t_hours: float, s: float = 1.25) -> float:
        t_hours = max(0.0, t_hours)
        s = max(0.01, s)
        return max(0.0, min(math.exp(-t_hours / s), 1.0))

    # ==========================================================
    # SINGLE MEMORY SCORE COMPUTATION
    # ==========================================================
    @safe_exec
    def compute_memory_score(
        last_review_time: datetime,
        lambda_val: float,
        intent_conf: float = 1.0,
        attention_score: Optional[float] = 50.0,
        audio_conf: float = 1.0,
        update_graph: bool = True,
        concept: Optional[str] = None
    ) -> float:
        if not isinstance(last_review_time, datetime):
            last_review_time = datetime.now()

        t_hours = max(0.0, (datetime.now() - last_review_time).total_seconds() / 3600)
        lambda_val = max(MIN_LAMBDA, lambda_val)
        R_t = math.exp(-lambda_val * t_hours)

        att_factor = max(0.0, min((attention_score or 0) / 100.0, 1.0))
        audio_factor = max(0.0, min(audio_conf, 1.0))
        intent_conf = max(0.0, min(intent_conf, 1.0))

        memory_score = R_t * intent_conf * att_factor * audio_factor
        memory_score = max(0.0, min(memory_score, 1.0))

        # Update knowledge graph
        if update_graph and concept:
            G = get_graph()
            if concept in G:
                G.nodes[concept]['memory_score'] = memory_score
                G.nodes[concept]['last_seen_ts'] = datetime.now().isoformat()

        return memory_score

    # ==========================================================
    # BATCH MEMORY SCORE COMPUTATION
    # ==========================================================
    @safe_exec
    def compute_memory_scores_batch(
        concepts: List[str],
        last_reviews: List[datetime],
        lambdas: Optional[List[float]] = None,
        intent_confs: Optional[List[float]] = None,
        attention_scores: Optional[List[float]] = None,
        audio_confs: Optional[List[float]] = None
    ) -> Dict[str, float]:
        results = {}
        lambdas = lambdas or [0.1] * len(concepts)
        intent_confs = intent_confs or [1.0] * len(concepts)
        attention_scores = attention_scores or [50.0] * len(concepts)
        audio_confs = audio_confs or [1.0] * len(concepts)

        for idx, concept in enumerate(concepts):
            score = compute_memory_score(
                last_reviews[idx],
                lambdas[idx],
                intent_confs[idx],
                attention_scores[idx],
                audio_confs[idx],
                update_graph=True,
                concept=concept
            )
            results[concept] = score

        return results

    # ==========================================================
    # NEXT REVIEW SCHEDULER
    # ==========================================================
    @safe_exec
    def schedule_next_review(
        last_review_time: datetime,
        memory_score: float,
        lambda_val: float,
        hours_min: float = 1.0
    ) -> datetime:
        memory_score = max(0.0, min(memory_score, 1.0))
        if memory_score < MEMORY_THRESHOLD:
            return datetime.now() + timedelta(hours=hours_min)
        lambda_val = max(MIN_LAMBDA, lambda_val)
        if not isinstance(last_review_time, datetime):
            last_review_time = datetime.now()
        return last_review_time + timedelta(hours=1 / lambda_val)

    # ==========================================================
    # LOG FORGETTING CURVE EVENT (ASYNC)
    # ==========================================================
    @safe_exec
    async def log_forgetting_curve(
        concept: str,
        last_seen_time: datetime,
        observed_usage: int = 1,
        memory_strength: float = 1.25
    ) -> float:
        if not isinstance(last_seen_time, datetime):
            last_seen_time = datetime.now()

        t_hours = max(0.0, (datetime.now() - last_seen_time).total_seconds() / 3600)
        predicted_recall = forgetting_curve(t_hours, memory_strength)

        # Async log
        await log_multi_modal_event_async(
            window_title=f"ForgettingCurve: {concept}",
            ocr_keywords=concept,
            audio_label=None,
            attention_score=None,
            interaction_rate=None,
            intent_label="memory_decay",
            intent_confidence=None,
            memory_score=predicted_recall,
            source_module="MemoryModel"
        )

        # Update knowledge graph
        G = get_graph()
        if concept in G:
            G.nodes[concept]['memory_score'] = predicted_recall
            G.nodes[concept]['last_seen_ts'] = datetime.now().isoformat()

        # Update metrics table
        next_review = schedule_next_review(last_seen_time, predicted_recall, lambda_val=0.1)
        update_metric(concept, next_review.isoformat(), predicted_recall)

        return max(0.0, min(predicted_recall, 1.0))

    # ==========================================================
    # SELF-TEST / DEMO
    # ==========================================================
    if __name__ == "__main__":
        import asyncio

        last_review = datetime.now() - timedelta(hours=5)
        memory_score = compute_memory_score(
            last_review, lambda_val=0.1, intent_conf=0.9, attention_score=80, audio_conf=1.0, concept="Photosynthesis"
        )
        next_review = schedule_next_review(last_review, memory_score, lambda_val=0.1)
        predicted_recall = asyncio.run(log_forgetting_curve("Photosynthesis", last_review, observed_usage=2))

        concepts = ["Photosynthesis", "Chlorophyll", "Mitochondria"]
        last_reviews = [datetime.now() - timedelta(hours=5),
                        datetime.now() - timedelta(hours=10),
                        datetime.now() - timedelta(hours=2)]
        batch_scores = compute_memory_scores_batch(concepts, last_reviews)

        print(f"Memory Score: {memory_score:.2f}")
        print(f"Next Review: {next_review}")
        print(f"Predicted Recall (logged async): {predicted_recall:.2f}")
        print("Batch Scores:", batch_scores)
