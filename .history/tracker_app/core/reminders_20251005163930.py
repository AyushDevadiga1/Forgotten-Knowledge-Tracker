# core/reminders.py
from datetime import datetime, timedelta
from plyer import notification

MEMORY_THRESHOLD = 0.6  # concepts below this score trigger reminders
COOLDOWN_MINUTES = 30   # minimum time between notifications per concept
MAX_NOTIFICATIONS_PER_CHECK = 5  # cap per check

def check_reminders(graph):
    """
    Loop through knowledge graph nodes and trigger reminders if needed.
    Uses cooldown to prevent flooding.
    """
    now = datetime.now()
    notifications_sent = 0

    # Sort nodes by memory score ascending (lower memory -> higher priority)
    nodes_sorted = sorted(graph.nodes(data=True), key=lambda x: x[1].get('memory_score', 1.0))

    for node, attrs in nodes_sorted:
        if notifications_sent >= MAX_NOTIFICATIONS_PER_CHECK:
            break

        mem_score = attrs.get('memory_score', 1.0)
        next_review = attrs.get('next_review_time', now)
        last_notif = attrs.get('last_notification', now - timedelta(hours=1))

        # Check if reminder is needed
        if mem_score < MEMORY_THRESHOLD or next_review <= now:
            # Check cooldown
            if (now - last_notif).total_seconds() >= COOLDOWN_MINUTES * 60:
                send_notification(node, mem_score)
                graph.nodes[node]['last_notification'] = now
                # Schedule next review safely (at least 1 hour later)
                graph.nodes[node]['next_review_time'] = now + timedelta(hours=1)
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
