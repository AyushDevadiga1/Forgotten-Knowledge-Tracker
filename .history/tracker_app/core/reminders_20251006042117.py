# core/reminders.py
"""
Reminder Management Module (IEEE-Ready)
---------------------------------------
- Triggers spaced-review reminders based on memory score and next review time.
- Logs notifications in file logs and persistently in the database.
- Fully typed, safe, and traceable.
"""

from datetime import datetime, timedelta
from plyer import notification
import logging
import traceback
import sqlite3
from typing import Optional
from core.knowledge_graph import get_graph
from core.db_module import init_multi_modal_db
from config import DB_PATH

# ==============================
# CONFIGURABLE PARAMETERS
# ==============================
MEMORY_THRESHOLD: float = 0.6          # Below this memory score, concept needs review
REMINDER_COOLDOWN_HOURS: float = 1     # Min time between notifications per concept
MAX_NOTIFICATIONS_PER_RUN: int = 5     # Prevent spamming on large graphs

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
def safe_parse_datetime(value) -> datetime:
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
        title: str = "⏰ Time to Review!"
        message: str = f"Concept: {concept}\nMemory Score: {memory_score:.2f}"
        notification.notify(title=title, message=message, timeout=5)
        logging.info(f"Notification sent for concept '{concept}' (score={memory_score:.2f})")
        return True
    except Exception as e:
        logging.error(f"Notification failed for {concept}: {e}\n{traceback.format_exc()}")
        return False


def log_reminder_to_db(concept: str, memory_score: float, timestamp: datetime):
    """Log the reminder to the multi_modal_logs table with extra trace info."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO multi_modal_logs (
                timestamp, window_title, ocr_keywords, audio_label,
                attention_score, interaction_rate, intent_label, intent_confidence, memory_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp.isoformat(),
            f"Reminder: {concept}",   # window_title
            concept,                   # ocr_keywords
            None,                      # audio_label
            None,                      # attention_score
            None,                      # interaction_rate
            "reminder",                # intent_label
            None,                      # intent_confidence
            memory_score
        ))
        conn.commit()
        conn.close()
        logging.info(f"Logged reminder for '{concept}' to DB.")
    except Exception as e:
        logging.error(f"Failed to log reminder to DB for '{concept}': {e}\n{traceback.format_exc()}")


# ==============================
# CORE FUNCTION
# ==============================
def check_reminders() -> int:
    """
    Loop through knowledge graph nodes and trigger reminders.
    - Handles graph safely
    - Prevents notification floods
    - Updates node metadata after reminders
    - Logs reminders to DB
    Returns:
        int: Number of notifications sent.
    """
    reminder_count: int = 0
    try:
        G = get_graph()
        now = datetime.now()

        for node in list(G.nodes):
            mem_score: float = float(G.nodes[node].get('memory_score', 1.0))
            next_review_time: datetime = safe_parse_datetime(G.nodes[node].get('next_review_time', now))
            last_reminded: datetime = safe_parse_datetime(
                G.nodes[node].get('last_reminded_time', now - timedelta(hours=REMINDER_COOLDOWN_HOURS + 1))
            )

            # Eligibility checks
            due_for_review: bool = mem_score < MEMORY_THRESHOLD or next_review_time <= now
            cooldown_passed: bool = (now - last_reminded).total_seconds() >= REMINDER_COOLDOWN_HOURS * 3600

            if due_for_review and cooldown_passed:
                if reminder_count >= MAX_NOTIFICATIONS_PER_RUN:
                    logging.warning("Max notification limit reached for this run.")
                    break

                if send_notification(node, mem_score):
                    reminder_count += 1
                    # Update KG metadata
                    G.nodes[node]['last_reminded_time'] = now.isoformat()
                    G.nodes[node]['next_review_time'] = (now + timedelta(hours=REMINDER_COOLDOWN_HOURS)).isoformat()
                    # Log reminder to database
                    log_reminder_to_db(node, mem_score, now)

        logging.info(f"✅ Reminder check complete. Total notifications sent: {reminder_count}")

    except Exception as e:
        logging.error(f"❌ Reminder check failed: {e}\n{traceback.format_exc()}")

    return reminder_count


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
    sent = check_reminders()
    print(f"✅ Reminder check finished. Total notifications sent: {sent} (check logs/reminders.log and DB)")
