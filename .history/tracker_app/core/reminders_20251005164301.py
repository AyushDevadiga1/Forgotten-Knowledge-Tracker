# core/reminders_db.py
import sqlite3
from datetime import datetime, timedelta
from plyer import notification
from core.c

MEMORY_THRESHOLD = 0.6
COOLDOWN_MINUTES = 30
MAX_NOTIFICATIONS_PER_CHECK = 5

def fetch_due_concepts():
    """
    Fetch concepts from DB with low memory score or past review time.
    Returns list of dicts: [{'concept': str, 'memory_score': float, 'next_review': datetime}]
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if memory_decay table exists
    try:
        c.execute("SELECT keyword, predicted_recall, last_seen_ts FROM memory_decay")
        rows = c.fetchall()
    except sqlite3.OperationalError:
        rows = []  # Table missing
    
    conn.close()
    
    concepts = []
    for row in rows:
        keyword, predicted_recall, last_seen_ts = row
        next_review = datetime.strptime(last_seen_ts, "%Y-%m-%d %H:%M:%S") + timedelta(hours=1)
        if predicted_recall < MEMORY_THRESHOLD or next_review <= datetime.now():
            concepts.append({
                "concept": keyword,
                "memory_score": predicted_recall,
                "next_review": next_review,
                "last_notification": datetime.now() - timedelta(hours=1)
            })
    
    return concepts

def check_reminders_db():
    """
    Check DB for concepts to notify. If DB empty, use test/demo data.
    """
    concepts = fetch_due_concepts()
    
    # If DB empty, create demo data
    if not concepts:
        now = datetime.now()
        concepts = [
            {"concept": "Photosynthesis", "memory_score": 0.5, "next_review": now - timedelta(minutes=1),
             "last_notification": now - timedelta(hours=1)},
            {"concept": "Chlorophyll", "memory_score": 0.4, "next_review": now - timedelta(minutes=10),
             "last_notification": now - timedelta(hours=1)}
        ]
    
    notifications_sent = 0
    now = datetime.now()
    
    # Sort by memory_score ascending
    concepts_sorted = sorted(concepts, key=lambda x: x['memory_score'])
    
    for c in concepts_sorted:
        if notifications_sent >= MAX_NOTIFICATIONS_PER_CHECK:
            break
        mem_score = c['memory_score']
        next_review = c['next_review']
        last_notif = c.get('last_notification', now - timedelta(hours=1))
        
        if mem_score < MEMORY_THRESHOLD or next_review <= now:
            if (now - last_notif).total_seconds() >= COOLDOWN_MINUTES * 60:
                send_notification(c['concept'], mem_score)
                c['last_notification'] = now
                notifications_sent += 1

def send_notification(concept, memory_score):
    """
    Trigger system notification safely.
    """
    title = "Time to Review!"
    message = f"Concept: {concept}\nMemory Score: {memory_score:.2f}"
    try:
        notification.notify(title=title, message=message, timeout=5)
        print(f"✅ Notification sent for '{concept}' with score {memory_score:.2f}")
    except Exception as e:
        print(f"⚠️ Failed to send notification for '{concept}': {e}")

# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    check_reminders_db()
