# core/reminders.py
from datetime import datetime, timedelta
from plyer import notification
from core.knowledge_graph import get_graph

# Configurable thresholds
MEMORY_THRESHOLD = 0.6       # Below this, trigger reminder
REMINDER_COOLDOWN_HOURS = 1  # Minimum time between notifications per concept

def safe_parse_datetime(value):
    """Convert ISO string or datetime to datetime object safely"""
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.now()

def check_reminders():
    """
    Loop through knowledge graph nodes and trigger reminders safely
    """
    now = datetime.now()
    G = get_graph()
    for node in G.nodes:
        mem_score = float(G.nodes[node].get('memory_score', 1.0))
        next_review_time = safe_parse_datetime(G.nodes[node].get('next_review_time', now))
        last_reminded = safe_parse_datetime(G.nodes[node].get('last_reminded_time', now - timedelta(hours=REMINDER_COOLDOWN_HOURS + 1)))

        # Check if memory low or scheduled for review AND cooldown passed
        if (mem_score < MEMORY_THRESHOLD or next_review_time <= now) and (now - last_reminded).total_seconds() >= REMINDER_COOLDOWN_HOURS * 3600:
            # Send system notification
            notification.notify(
                title="Time to Review!",
                message=f"Concept: {node}\nMemory Score: {mem_score:.2f}",
                timeout=5
            )
            # Update last reminded timestamp
            G.nodes[node]['last_reminded_time'] = now.isoformat()
            # Optionally push next review to avoid repeated notifications
            G.nodes[node]['next_review_time'] = (now + timedelta(hours=REMINDER_COOLDOWN_HOURS)).isoformat()

                notifications_sent += 1

def send_notification(concept, memory_score):
    """
    Trigger system notification safely.
    """
    title = "Time to Review!"
    message = f"Concept: {concept}\nMemory Score: {memory_score:.2f}"
    notification.notify(title=title, message=message, timeout=5)  # 5 sec notification

# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    import networkx as nx

    # Create test graph
    G = nx.Graph()
    now = datetime.now()
    G.add_node("Photosynthesis", memory_score=0.5, next_review_time=now - timedelta(minutes=1))
    G.add_node("Chlorophyll", memory_score=0.4, next_review_time=now - timedelta(minutes=10))
    G.add_node("Respiration", memory_score=0.8, next_review_time=now + timedelta(hours=1))
    
    # Run reminder check
    check_reminders(G)
