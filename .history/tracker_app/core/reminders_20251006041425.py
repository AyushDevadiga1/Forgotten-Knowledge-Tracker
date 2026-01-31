# core/reminders.py
"""
Reminder Management Module
---------------------------
IEEE-grade enhancement for reliability, traceability, adaptive cognitive reminders,
and persistent logging of reminders in the database.
"""

from datetime import datetime, timedelta
from plyer import notification
import logging
import traceback
import sqlite3
from core.knowledge_graph import get_graph
from core.db_module import init_multi_modal_db
from config import DB_PATH

# ==============================
# CONFIGURABLE PARAMETERS
# ==============================
MEMORY_THRESHOLD = 0.6          # Below this memory score, concept needs review
REMINDER_COOLDOWN_HOURS = 1     # Min time between notifications per concept
MAX_NOTIFICATIONS_PER_RUN = 5   # Prevent spamming on large graphs

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
init_multi_modal_db()  # Ensure multi-modal logs table exists

# ==============================
# UTILITY FUNCTIONS
# ==============================
def safe_parse_datetime(value):
    """Convert ISO string or datetime to datetime object safely."""
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        logging.warning(f"Invalid datetime format encountered: {value}")
        return datetime.now()


def send_notification(concept: str, memory_score: float) -> bool:
    """
    Trigger system notification safely with exception handling.
    Returns True if sent successfully, else False.
    """
    try:
        title = "⏰ Time to Review!"
        message = f"Concept: {concept}\nMemory Score: {memory_score:.2f}"
        notification.notify(title=title, message=message, timeout=5)
        logging.info(f"Notification sent for concept '{concept}' (score={memory_score:.2f})")
        return True
    except Exception as e:
        logging.error(f"Notification failed for {concept}: {e}\n{traceback.format_exc()}")
        return False


def log_reminder_to_db(concept: str, memory_score: float, timestamp: datetime):
    """Log the reminder to the multi_modal_logs table"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO multi_modal_logs (timestamp, ocr_keywords, memory_score)
            VALUES (?, ?, ?)
        """, (timestamp.isoformat(), concept, memory_score))
        conn.commit()
        conn.close()
        logging.info(f"Logged reminder for '{concept}' to DB.")
    except Exception as e:
        logging.error(f"Failed to log reminder to DB for '{concept}': {e}")


# ==============================
# CORE FUNCTION
# ==============================
def check_reminders():
    """
    Loop through knowledge graph nodes and trigger reminders.
    - Handles graph safely
    - Prevents notification floods
    - Updates node metadata after reminders
    - Logs reminders to DB
    """
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

            # Eligibility checks
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

                    # Log reminder to database
                    log_reminder_to_db(node, mem_score, now)

        logging.info(f"✅ Reminder check complete. Total notifications sent: {reminder_count}")

    except Exception as e:
        logging.error(f"❌ Reminder check failed: {e}\n{traceback.format_exc()}")


# ==============================
# SELF-TEST (Safe Demo)
# ==============================
if __name__ == "__main__":
    import networkx as nx
    G = nx.Graph()
    now = datetime.now()

    G.add_node("Photosynthesis", memory_score=0.5, next_review_time=now - timedelta(minutes=1))
    G.add_node("Chlorophyll", memory_score=0.4, next_review_time=now - timedelta(minutes=10))
    G.add_node("Respiration", memory_score=0.8, next_review_time=now + timedelta(hours=1))

    print("🔍 Running self-test for reminders module...")
    check_reminders()
    print("✅ Reminder check finished (check logs/reminders.log for output).")
