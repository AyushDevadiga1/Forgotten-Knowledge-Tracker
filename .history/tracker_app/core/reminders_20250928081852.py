from datetime import datetime
from plyer import notification

MEMORY_THRESHOLD = 0.6  # concepts below this score trigger reminders

def check_reminders(graph):
    """
    Loop through knowledge graph nodes and trigger reminders if needed
    """
    now = datetime.now()
    for node in graph.nodes:
        mem_score = graph.nodes[node].get('memory_score', 1.0)
        next_review = graph.nodes[node].get('next_review_time', now)
        
        if mem_score < MEMORY_THRESHOLD or next_review <= now:
            send_notification(node, mem_score)
            # Update next_review_time to avoid multiple notifications
            graph.nodes[node]['next_review_time'] = now + timedelta(hours=1)

def send_notification(concept, memory_score):
    """
    Trigger system notification
    """
    title = "Time to Review!"
    message = f"Concept: {concept}\nMemory Score: {memory_score:.2f}"
    notification.notify(title=title, message=message, timeout=5)  # 5 sec notification

# Example usage
if __name__ == "__main__":
    import networkx as nx
    from datetime import datetime, timedelta
    
    G = nx.Graph()
    G.add_node("Photosynthesis", memory_score=0.5, next_review_time=datetime.now() - timedelta(minutes=1))
    
    check_reminders(G)
