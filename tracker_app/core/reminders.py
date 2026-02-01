# core/reminders.py
from datetime import datetime, timedelta
from plyer import notification
from tracker_app.core.knowledge_graph import get_graph

# Configurable thresholds
MEMORY_THRESHOLD = 0.6       # Below this, trigger reminder
REMINDER_COOLDOWN_HOURS = 1  # Minimum time between notifications per concept

def safe_parse_datetime(value, default=None):
    """Convert ISO string or datetime to datetime object safely"""
    if default is None:
        default = datetime.now()
        
    if isinstance(value, datetime):
        return value
    elif isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            try:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                return default
    else:
        return default

def check_reminders():
    """
    Loop through knowledge graph nodes and trigger reminders safely
    """
    try:
        now = datetime.now()
        G = get_graph()
        reminders_sent = 0
        
        for node in list(G.nodes):
            try:
                node_data = G.nodes[node]
                
                # Skip if node doesn't have required data
                if not isinstance(node_data, dict):
                    continue
                    
                # Get memory score with default
                mem_score = float(node_data.get('memory_score', 1.0))
                
                # Get next review time
                next_review_str = node_data.get('next_review_time')
                next_review_time = safe_parse_datetime(next_review_str, now + timedelta(days=1))
                
                # Get last reminded time
                last_reminded_str = node_data.get('last_reminded_time')
                last_reminded = safe_parse_datetime(last_reminded_str, now - timedelta(hours=REMINDER_COOLDOWN_HOURS + 1))
                
                # Calculate time since last reminder
                time_since_last_reminder = now - last_reminded
                
                # Check conditions for reminder
                memory_low = mem_score < MEMORY_THRESHOLD
                review_due = next_review_time <= now
                cooldown_passed = time_since_last_reminder.total_seconds() >= REMINDER_COOLDOWN_HOURS * 3600
                
                if (memory_low or review_due) and cooldown_passed:
                    # Send notification
                    send_notification(node, mem_score)
                    reminders_sent += 1
                    
                    # Update node data
                    G.nodes[node]['last_reminded_time'] = now.isoformat()
                    G.nodes[node]['next_review_time'] = (now + timedelta(hours=REMINDER_COOLDOWN_HOURS)).isoformat()
                    
            except Exception as e:
                print(f"Error processing reminder for node {node}: {e}")
                continue
        
        if reminders_sent > 0:
            print(f"Sent {reminders_sent} reminder(s)")
        else:
            print("No reminders needed at this time")
            
        return reminders_sent
        
    except Exception as e:
        print(f"Error in check_reminders: {e}")
        return 0

def send_notification(concept, memory_score):
    """
    Trigger system notification safely.
    """
    try:
        title = "🔄 Time to Review!"
        message = f"Concept: {concept}\nMemory Score: {memory_score:.2f}\n\nClick to focus and review this concept."
        
        notification.notify(
            title=title,
            message=message,
            timeout=10,  # 10 seconds
            app_name="Forgotten Knowledge Tracker"
        )
        
        print(f"Notification sent: {concept} (score: {memory_score:.2f})")
        
    except Exception as e:
        print(f"Error sending notification: {e}")

def get_upcoming_reminders(hours_ahead=24):
    """
    Get list of concepts that will need review in the next specified hours
    """
    try:
        now = datetime.now()
        future = now + timedelta(hours=hours_ahead)
        G = get_graph()
        
        upcoming = []
        
        for node in G.nodes:
            try:
                node_data = G.nodes[node]
                next_review_str = node_data.get('next_review_time')
                next_review = safe_parse_datetime(next_review_str, now + timedelta(days=1))
                mem_score = float(node_data.get('memory_score', 1.0))
                
                # Check if review is due within the time window
                if now <= next_review <= future:
                    upcoming.append({
                        'concept': node,
                        'next_review': next_review,
                        'memory_score': mem_score,
                        'hours_until': (next_review - now).total_seconds() / 3600
                    })
                    
            except Exception as e:
                print(f"Error checking upcoming reminder for {node}: {e}")
                continue
        
        # Sort by review time
        upcoming.sort(key=lambda x: x['next_review'])
        return upcoming
        
    except Exception as e:
        print(f"Error getting upcoming reminders: {e}")
        return []

def manual_reminder(concept):
    """
    Manually trigger a reminder for a specific concept
    """
    try:
        G = get_graph()
        
        if concept not in G.nodes:
            print(f"Concept '{concept}' not found in knowledge graph")
            return False
            
        mem_score = float(G.nodes[concept].get('memory_score', 0.5))
        send_notification(concept, mem_score)
        
        # Update last reminded time
        G.nodes[concept]['last_reminded_time'] = datetime.now().isoformat()
        
        return True
        
    except Exception as e:
        print(f"Error sending manual reminder: {e}")
        return False

# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    # Check for due reminders
    reminders_sent = check_reminders()
    print(f"Sent {reminders_sent} reminders")
    
    # Get upcoming reminders
    upcoming = get_upcoming_reminders(24)
    print(f"Upcoming reminders in next 24 hours: {len(upcoming)}")
    
    for reminder in upcoming[:5]:  # Show first 5
        print(f"  - {reminder['concept']}: {reminder['hours_until']:.1f}h (score: {reminder['memory_score']:.2f})")