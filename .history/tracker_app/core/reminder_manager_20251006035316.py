# core/reminder_manager.py
from datetime import datetime, timedelta
from plyer import notification
import sqlite3
from config import DB_PATH
import logging

# -----------------------------
# Configurable thresholds
# -----------------------------
MEMORY_THRESHOLD = 0.6
REMINDER_COOLDOWN_HOURS = 1

# -----------------------------
# Logging setup
# -----------------------------
logging.basicConfig(
    filename="reminder_manager.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# -----------------------------
# DB Utilities
# -----------------------------
def fetch_memory_decay():
    """Fetch all concepts with memory scores from memory_decay table"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT keyword, last_seen_ts, predicted_recall, updated_at FROM memory_decay")
    rows = c.fetchall()
    conn.close()
    return rows

def update_last_reminder(keyword):
    """Update the last reminder timestamp in memory_decay"""
    now = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE memory_decay SET updated_at=? WHERE keyword=?", (now, keyword))
    conn.commit()
    conn.close()

# -----------------------------
# Safe datetime parsing
# -----------------------------
def safe_parse_datetime(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.now()

# -----------------------------
# Reminder logic
# -----------------------------
def check_reminders():
    """Check all concepts and trigger notifications if needed"""
    now = datetime.now()
    rows = fetch_memory_decay()
    for row in rows:
        keyword, last_seen_ts, predicted_recall, updated_at = row
        mem_score = float(predicted_recall or 1.0)
        last_reminded = safe_parse_datetime(updated_at or (now - timedelta(hours=REMINDER_COOLDOWN_HOURS + 1)))
        last_seen = safe_parse_datetime(last_seen_ts or now)

        # Trigger conditions
        if (mem_score < MEMORY_THRESHOLD or last_seen <= now) and (now - last_reminded).total_seconds() >= REMINDER_COOLDOWN_HOURS * 3600:
            try:
                # Send notification
                notification.notify(
                    title="Time to Review!",
                    message=f"Concept: {keyword}\nMemory Score: {mem_score:.2f}",
                    timeout=5
                )
                logging.info(f"Reminder sent for {keyword} (Memory: {mem_score:.2f})")
                # Update last reminder timestamp
                update_last_reminder(keyword)
            except Exception as e:
                logging.error(f"Failed to send reminder for {keyword}: {e}")

# -----------------------------
# Optional test run
# -----------------------------
if __name__ == "__main__":
    check_reminders()
