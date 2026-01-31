# ==========================================================
# core/reminders.py
# ==========================================================

"""
Reminder Management Module (IEEE-Ready v5)
-------------------------------------------
- Multi-modal aware (attention, interactions & webcam)
- Priority-based reminders
- Batch notifications support
- Dynamic non-linear cooldowns based on memory score
- Retry-safe notifications
- Logs notifications in DB & file logs
"""

from datetime import datetime, timedelta
from plyer import notification
import logging
import traceback
from typing import Optional, List, Tuple
from core.knowledge_graph import get_graph
from core.db_module import init_multi_modal_db, log_multi_modal_event
import numpy as np
import asyncio

# ==============================
# CONFIGURABLE PARAMETERS
# ==============================
MEMORY_THRESHOLD: float = 0.6
BASE_COOLDOWN_HOURS: float = 1
MAX_NOTIFICATIONS_PER_RUN: int = 5
BATCH_NOTIFICATION: bool = True
ATTENTION_REQUIRED: bool = True
WEBCAM_REQUIRED: bool = True

# ==============================
# LOGGER SETUP
# ==============================
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ==============================
# INITIALIZE DATABASE TABLE
# ==============================
init_multi_modal_db()

# ==============================
# UTILITY FUNCTIONS
# ==============================
def safe_parse_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        logger.warning(f"Invalid datetime format encountered: {value}")
        return datetime.now()

def compute_dynamic_cooldown(mem_score: float, base_hours: float = BASE_COOLDOWN_HOURS) -> float:
    """Non-linear cooldown: lower memory => shorter cooldown"""
    cooldown = base_hours * np.exp(mem_score - 1)
    return max(0.1, cooldown)

async def safe_notification_send(func, *args, retries: int = 2, delay_sec: float = 0.5, **kwargs) -> bool:
    """Async retry wrapper for notifications"""
    attempt = 0
    while attempt <= retries:
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except Exception as e:
            logger.warning(f"Notification attempt {attempt+1} failed: {e}")
            attempt += 1
            await asyncio.sleep(delay_sec)
    return False

def format_notification_message(concepts: List[str], scores: List[float], last_review_times: List[datetime]) -> str:
    """Format message with memory score and last review delta"""
    now = datetime.now()
    lines = [f"{c} (score={s:.2f}, last reviewed {int((now-t).total_seconds()/60)} min ago)"
             for c, s, t in zip(concepts, scores, last_review_times)]
    return "\n".join(lines)

# ==============================
# NOTIFICATION FUNCTIONS
# ==============================
def send_notification_batch(concepts: List[str], scores: List[float]) -> bool:
    try:
        message = "\n".join([f"{c} (score={s:.2f})" for c, s in zip(concepts, scores)])
        notification.notify(title="⏰ Review Reminder!", message=message, timeout=8)
        logger.info(f"Batch notification sent for {len(concepts)} concepts.")
        return True
    except Exception as e:
        logger.error(f"Batch notification failed: {e}\n{traceback.format_exc()}")
        return False

def send_notification_single(concept: str, memory_score: float) -> bool:
    try:
        notification.notify(title="⏰ Time to Review!", message=f"{concept}\nMemory Score: {memory_score:.2f}", timeout=5)
        logger.info(f"Notification sent for '{concept}' (score={memory_score:.2f})")
        return True
    except Exception as e:
        logger.error(f"Notification failed for {concept}: {e}\n{traceback.format_exc()}")
        return False

# ==============================
# CORE FUNCTION
# ==============================
async def check_reminders(attention_score: Optional[int] = None,
                          interaction_rate: Optional[int] = None,
                          webcam_active: Optional[bool] = True) -> int:
    reminder_count = 0
    try:
        G = get_graph()
        now = datetime.now()
        due_nodes: List[Tuple[str, float, datetime]] = []

        # Determine eligible nodes
        for node in list(G.nodes):
            mem_score = float(G.nodes[node].get('memory_score', 1.0))
            next_review_time = safe_parse_datetime(G.nodes[node].get('next_review_time', now))
            last_reminded = safe_parse_datetime(G.nodes[node].get(
                'last_reminded_time', now - timedelta(hours=BASE_COOLDOWN_HOURS + 1)
            ))
            cooldown_hours = compute_dynamic_cooldown(mem_score)
            due_for_review = mem_score < MEMORY_THRESHOLD or next_review_time <= now
            cooldown_passed = (now - last_reminded).total_seconds() >= cooldown_hours * 3600

            # Attention & webcam gating
            attention_ok = True
            if ATTENTION_REQUIRED and attention_score is not None and attention_score < 20:
                attention_ok = False
            if WEBCAM_REQUIRED and not webcam_active:
                attention_ok = False

            if due_for_review and cooldown_passed and attention_ok:
                due_nodes.append((node, mem_score, last_reminded))

        due_nodes.sort(key=lambda x: x[1])  # lowest memory score first

        # Send notifications
        if BATCH_NOTIFICATION and due_nodes:
            batch_nodes, batch_scores, batch_last = zip(*due_nodes[:MAX_NOTIFICATIONS_PER_RUN])
            if await safe_notification_send(send_notification_batch, list(batch_nodes), list(batch_scores)):
                reminder_count += len(batch_nodes)
                for n, s in zip(batch_nodes, batch_scores):
                    G.nodes[n]['last_reminded_time'] = now.isoformat()
                    G.nodes[n]['next_review_time'] = (now + timedelta(hours=BASE_COOLDOWN_HOURS)).isoformat()
                    log_multi_modal_event(
                        window_title=f"Reminder: {n}",
                        ocr_keywords=n,
                        audio_label=None,
                        attention_score=attention_score,
                        interaction_rate=interaction_rate,
                        intent_label="reminder",
                        intent_confidence=None,
                        memory_score=s,
                        source_module="Reminders"
                    )
        else:
            for n, s, last in due_nodes[:MAX_NOTIFICATIONS_PER_RUN]:
                if await safe_notification_send(send_notification_single, n, s):
                    reminder_count += 1
                    G.nodes[n]['last_reminded_time'] = now.isoformat()
                    G.nodes[n]['next_review_time'] = (now + timedelta(hours=BASE_COOLDOWN_HOURS)).isoformat()
                    log_multi_modal_event(
                        window_title=f"Reminder: {n}",
                        ocr_keywords=n,
                        audio_label=None,
                        attention_score=attention_score,
                        interaction_rate=interaction_rate,
                        intent_label="reminder",
                        intent_confidence=None,
                        memory_score=s,
                        source_module="Reminders"
                    )

        logger.info(f"✅ Reminder check complete. Total notifications sent: {reminder_count}")

    except Exception as e:
        logger.error(f"❌ Reminder check failed: {e}\n{traceback.format_exc()}")

    return reminder_count

# ==============================
# SELF-TEST
# ==============================
if __name__ == "__main__":
    import networkx as nx
    G = nx.Graph()
    now = datetime.now()
    G.add_node("Photosynthesis", memory_score=0.5, next_review_time=now - timedelta(minutes=1))
    G.add_node("Chlorophyll", memory_score=0.4, next_review_time=now - timedelta(minutes=10))
    G.add_node("Respiration", memory_score=0.8, next_review_time=now + timedelta(hours=1))

    print("🔍 Running self-test for reminders module...")
    sent = asyncio.run(check_reminders(attention_score=50, interaction_rate=10, webcam_active=True))
    print(f"✅ Reminder check finished. Total notifications sent: {sent} (check logs/reminders.log and DB)")
