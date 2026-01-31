# core/reminders.py
"""
Reminder Management Module (IEEE-Ready v3)
-------------------------------------------
- Multi-modal aware (attention & interactions)
- Priority-based reminders
- Batch notifications support
- Dynamic cooldowns based on memory score
- Logs notifications in DB & file logs
"""

from datetime import datetime, timedelta
from plyer import notification
import logging
import traceback
from typing import Optional, List
from core.knowledge_graph import get_graph
from core.db_module import init_multi_modal_db, log_multi_modal_event

# ==============================
# CONFIGURABLE PARAMETERS
# ==============================
MEMORY_THRESHOLD: float = 0.6
BASE_COOLDOWN_HOURS: float = 1
MAX_NOTIFICATIONS_PER_RUN: int = 5
BATCH_NOTIFICATION: bool = True  # combine reminders into one pop-up
ATTENTION_REQUIRED: bool = True  # skip reminders if attention low or webcam off

# ==============================
# LOGGER SETUP
# ==============================
logging.basicConfig(
    filename="logs/reminders.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

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
        logging.warning(f"Invalid datetime format encountered: {value}")
        return datetime.now()


def send_notification_batch(concepts: List[str], scores: List[float]) -> bool:
    """Send a single batch notification for multiple concepts."""
    try:
        title = "⏰ Review Reminder!"
        message_lines = [f"{c} (score={s:.2f})" for c, s in zip(concepts, scores)]
        message = "\n".join(message_lines)
        notification.notify(title=title, message=message, timeout=8)
        logging.info(f"Batch notification sent for {len(concepts)} concepts.")
        return True
    except Exception as e:
        logging.error(f"Batch notification failed: {e}\n{traceback.format_exc()}")
        return False


def send_notification_single(concept: str, memory_score: float) -> bool:
    try:
        title = "⏰ Time to Review!"
        message = f"{concept}\nMemory Score: {memory_score:.2f}"
        notification.notify(title=title, message=message, timeout=5)
        logging.info(f"Notification sent for concept '{concept}' (score={memory_score:.2f})")
        return True
    except Exception as e:
        logging.error(f"Notification failed for {concept}: {e}\n{traceback.format_exc()}")
        return False


# ==============================
# CORE FUNCTION
# ==============================
def check_reminders(attention_score: Optional[int] = None, interaction_rate: Optional[int] = None) -> int:
    reminder_count = 0
    try:
        G = get_graph()
        now = datetime.now()
        due_nodes = []

        # Determine eligible nodes
        for node in list(G.nodes):
            mem_score = float(G.nodes[node].get('memory_score', 1.0))
            next_review_time = safe_parse_datetime(G.nodes[node].get('next_review_time', now))
            last_reminded = safe_parse_datetime(
                G.nodes[node].get('last_reminded_time', now - timedelta(hours=BASE_COOLDOWN_HOURS + 1))
            )

            # Dynamic cooldown: lower memory_score => shorter cooldown
            cooldown_hours = max(0.1, BASE_COOLDOWN_HOURS * mem_score)

            due_for_review = mem_score < MEMORY_THRESHOLD or next_review_time <= now
            cooldown_passed = (now - last_reminded).total_seconds() >= cooldown_hours * 3600

            attention_ok = True
            if ATTENTION_REQUIRED:
                if attention_score is not None and attention_score < 20:
                    attention_ok = False

            if due_for_review and cooldown_passed and attention_ok:
                due_nodes.append((node, mem_score))

        # Sort by urgency (lowest memory score first)
        due_nodes.sort(key=lambda x: x[1])

        # Send notifications
        if BATCH_NOTIFICATION and due_nodes:
            batch_nodes, batch_scores = zip(*due_nodes[:MAX_NOTIFICATIONS_PER_RUN])
            if send_notification_batch(list(batch_nodes), list(batch_scores)):
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
            for n, s in due_nodes[:MAX_NOTIFICATIONS_PER_RUN]:
                if send_notification_single(n, s):
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

        logging.info(f"✅ Reminder check complete. Total notifications sent: {reminder_count}")

    except Exception as e:
        logging.error(f"❌ Reminder check failed: {e}\n{traceback.format_exc()}")

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
    sent = check_reminders(attention_score=50, interaction_rate=10)
    print(f"✅ Reminder check finished. Total notifications sent: {sent} (check logs/reminders.log and DB)")
