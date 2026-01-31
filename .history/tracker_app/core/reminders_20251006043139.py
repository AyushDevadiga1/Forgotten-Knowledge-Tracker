# core/reminders.py
from datetime import datetime, timedelta
from plyer import notification
import logging
import traceback
from core.knowledge_graph import get_graph
from core.db_module import init_multi_modal_db, log_multi_modal_event
from config import DB_PATH

MEMORY_THRESHOLD = 0.6
REMINDER_COOLDOWN_HOURS = 1
MAX_NOTIFICATIONS_PER_RUN = 5

logging.basicConfig(
    filename="logs/reminders.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Ensure table exists
init_multi_modal_db()

def safe_parse_datetime(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        logging.warning(f"Invalid datetime format: {value}")
        return datetime.now()

def send_notification(concept: str, memory_score: float) -> bool:
    try:
        title = "⏰ Time to Review!"
        message = f"Concept: {concept}\nMemory Score: {memory_score:.2f}"
        notification.notify(title=title, message=message, timeout=5)
        logging.info(f"Notification sent for '{concept}' (score={memory_score:.2f})")
        return True
    except Exception as e:
        logging.error(f"Notification failed for {concept}: {e}\n{traceback.format_exc()}")
        return False

def check_reminders():
    try:
        G = get_graph()
        now = datetime.now()
        reminder_count = 0

        for node in list(G.nodes):
            mem_score = float(G.nodes[node].get('memory_score', 1.0))
            next_review_time = safe_parse_datetime(G.nodes[node].get('next_review_time', now))
            last_reminded = safe_parse_datetime(
                G.nodes[node].get('last_reminded_time', now - timedelta(hours=REMINDER_COOLDOWN_HOURS + 1))
            )

            due_for_review = mem_score < MEMORY_THRESHOLD or next_review_time <= now
            cooldown_passed = (now - last_reminded).total_seconds() >= REMINDER_COOLDOWN_HOURS * 3600

            if due_for_review and cooldown_passed:
                if reminder_count >= MAX_NOTIFICATIONS_PER_RUN:
                    logging.warning("Max notification limit reached for this run.")
                    break

                if send_notification(node, mem_score):
                    reminder_count += 1
                    G.nodes[node]['last_reminded_time'] = now.isoformat()
                    G.nodes[node]['next_review_time'] = (now + timedelta(hours=REMINDER_COOLDOWN_HOURS)).isoformat()

                    # --- Unified DB logging ---
                    log_multi_modal_event(
                        window_title=node,
                        memory_score=mem_score,
                        source_module="Reminders"
                    )

        logging.info(f"✅ Reminder check complete. Notifications sent: {reminder_count}")

    except Exception as e:
        logging.error(f"❌ Reminder check failed: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    import networkx as nx
    G = nx.Graph()
    now = datetime.now()
    G.add_node("Photosynthesis", memory_score=0.5, next_review_time=now - timedelta(minutes=1))
    G.add_node("Chlorophyll", memory_score=0.4, next_review_time=now - timedelta(minutes=10))
    G.add_node("Respiration", memory_score=0.8, next_review_time=now + timedelta(hours=1))

    print("🔍 Running self-test for reminders...")
    check_reminders()
    print("✅ Reminder check finished. Check logs/reminders.log and DB table.")
