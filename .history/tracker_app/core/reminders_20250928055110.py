from datetime import datetime, timedelta
from plyer import notification
import logging
from config import MEMORY_THRESHOLD
from core.sm2_scheduler import sm2_scheduler  # NEW

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NEW: Adaptive reminder system
class AdaptiveReminderSystem:
    def __init__(self, base_threshold=MEMORY_THRESHOLD):
        self.base_threshold = base_threshold
        self.reminder_history = []
        self.user_responsiveness = 1.0  # 1.0 = highly responsive, 0.0 = unresponsive
    
    def calculate_adaptive_threshold(self, time_of_day, day_of_week, recent_activity):
        """
        Calculate adaptive threshold based on context
        """
        threshold = self.base_threshold
        
        # Time of day adjustment (lower threshold during productive hours)
        hour = time_of_day.hour
        if 9 <= hour <= 17:  # Working hours
            threshold -= 0.1  # More sensitive during work hours
        elif 22 <= hour or hour <= 6:  # Late night/early morning
            threshold += 0.1  # Less sensitive during sleep hours
        
        # Day of week adjustment (lower threshold on weekdays)
        if day_of_week < 5:  # Weekday
            threshold -= 0.05
        else:  # Weekend
            threshold += 0.05
        
        # Activity-based adjustment
        if recent_activity > 10:  # High activity
            threshold -= 0.05
        elif recent_activity < 2:  # Low activity
            threshold += 0.05
        
        return max(0.3, min(0.8, threshold))  # Keep within reasonable bounds
    
    def update_user_responsiveness(self, reminder_accepted=True, response_time=0):
        """
        Update user responsiveness based on reminder interactions
        """
        if reminder_accepted:
            # Positive response improves responsiveness score
            self.user_responsiveness = min(1.0, self.user_responsiveness + 0.1)
        else:
            # Negative response decreases responsiveness score
            self.user_responsiveness = max(0.3, self.user_responsiveness - 0.1)
        
        # Adjust threshold based on responsiveness
        self.base_threshold = MEMORY_THRESHOLD * self.user_responsiveness
    
    def should_remind(self, concept_data, current_context):
        """
        Enhanced decision logic for reminders
        """
        mem_score = concept_data.get('memory_score', 1.0)
        next_review = concept_data.get('next_review_time', datetime.now())
        
        if isinstance(next_review, str):
            next_review = datetime.fromisoformat(next_review)
        
        now = datetime.now()
        
        # Calculate adaptive threshold
        adaptive_threshold = self.calculate_adaptive_threshold(
            now, now.weekday(), current_context.get('interaction_rate', 0)
        )
        
        # Base condition: memory score below threshold or review overdue
        base_condition = mem_score < adaptive_threshold or next_review <= now
        
        # Additional factors
        concept_importance = concept_data.get('count', 1)  # More frequent concepts are more important
        time_since_last_reminder = self.get_time_since_last_reminder(concept_data.get('concept', ''))
        
        # Don't remind too frequently for the same concept
        if time_since_last_reminder < timedelta(hours=1):
            return False
        
        # Boost importance for frequently encountered concepts
        importance_boost = min(concept_importance / 10, 0.3)  # Max 30% boost
        effective_threshold = adaptive_threshold - importance_boost
        
        return mem_score < effective_threshold or next_review <= now
    
    def get_time_since_last_reminder(self, concept):
        """Get time since last reminder for a concept"""
        for reminder in reversed(self.reminder_history):
            if reminder['concept'] == concept:
                return datetime.now() - reminder['timestamp']
        return timedelta(days=365)  # Large delta if no previous reminder

# Initialize adaptive reminder system
adaptive_reminder = AdaptiveReminderSystem()

# NEW: Enhanced reminder checking with context
def check_reminders_enhanced(graph, current_context=None):
    """
    Enhanced reminder system with context awareness
    """
    if current_context is None:
        current_context = {}
    
    now = datetime.now()
    reminders_triggered = 0
    
    for node in graph.nodes:
        node_data = graph.nodes[node]
        
        if adaptive_reminder.should_remind(node_data, current_context):
            # Send notification
            send_enhanced_notification(node, node_data, current_context)
            reminders_triggered += 1
            
            # Update reminder history
            adaptive_reminder.reminder_history.append({
                'concept': node,
                'timestamp': now,
                'memory_score': node_data.get('memory_score', 0.3),
                'context': current_context
            })
            
            # Update next review time with adaptive scheduling
            next_review = calculate_adaptive_review_interval(node_data, current_context)
            graph.nodes[node]['next_review_time'] = next_review
            
            # Limit reminders per check to avoid notification spam
            if reminders_triggered >= 3:
                break
    
    if reminders_triggered > 0:
        logger.info(f"Triggered {reminders_triggered} reminders")
    
    return reminders_triggered

# NEW: Adaptive review interval calculation
def calculate_adaptive_review_interval(concept_data, context):
    """
    Calculate adaptive review interval based on context and user responsiveness
    """
    base_interval = timedelta(hours=1)
    
    # Adjust based on memory score (lower score = shorter interval)
    mem_score = concept_data.get('memory_score', 0.3)
    score_factor = max(0.5, mem_score)  # 0.5 to 1.0 multiplier
    
    # Adjust based on time of day
    hour = datetime.now().hour
    if 22 <= hour or hour <= 6:  # Night hours - longer interval
        time_factor = 1.5
    elif 9 <= hour <= 17:  # Work hours - shorter interval
        time_factor = 0.7
    else:  # Evening hours - normal interval
        time_factor = 1.0
    
    # Adjust based on user activity
    activity = context.get('interaction_rate', 0)
    activity_factor = 1.0 - (min(activity, 20) / 100)  # 0.8 to 1.0
    
    adaptive_interval = base_interval * score_factor * time_factor * activity_factor
    
    # Ensure reasonable bounds
    min_interval = timedelta(minutes=30)
    max_interval = timedelta(days=7)
    
    return max(min_interval, min(max_interval, adaptive_interval))

# NEW: Enhanced notification with context
def send_enhanced_notification(concept, concept_data, context):
    """
    Send enhanced notification with context information
    """
    mem_score = concept_data.get('memory_score', 0.3)
    next_review = concept_data.get('next_review_time', datetime.now())
    interval = concept_data.get('interval', 1)
    
    # Create informative message
    title = "🕒 Time to Review!"
    
    message_lines = [
        f"Concept: {concept}",
        f"Memory Score: {mem_score:.2f}",
        f"Interval: {interval} days",
    ]
    
    # Add context information if available
    if context.get('app_type'):
        message_lines.append(f"Context: {context['app_type']}")
    
    if context.get('intent_label'):
        message_lines.append(f"Activity: {context['intent_label']}")
    
    message = "\n".join(message_lines)
    
    try:
        notification.notify(
            title=title,
            message=message,
            timeout=10,  # Longer timeout for more information
            app_name="Forgotten Knowledge Tracker"
        )
        logger.info(f"Sent reminder for: {concept}")
    except Exception as e:
        logger.error(f"Notification failed: {e}")

# NEW: Reminder analytics
def get_reminder_analytics():
    """Get analytics about reminder performance"""
    history = adaptive_reminder.reminder_history
    
    if not history:
        return {
            "total_reminders": 0,
            "avg_memory_score": 0,
            "user_responsiveness": adaptive_reminder.user_responsiveness
        }
    
    recent_reminders = [r for r in history if datetime.now() - r['timestamp'] < timedelta(days=7)]
    memory_scores = [r['memory_score'] for r in recent_reminders]
    
    return {
        "total_reminders": len(history),
        "recent_reminders": len(recent_reminders),
        "avg_memory_score": sum(memory_scores) / len(memory_scores) if memory_scores else 0,
        "user_responsiveness": adaptive_reminder.user_responsiveness,
        "adaptive_threshold": adaptive_reminder.base_threshold
    }

# ORIGINAL FUNCTIONS - PRESERVED
def check_reminders(graph):
    """
    ORIGINAL: Loop through knowledge graph nodes and trigger reminders if needed
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
    ORIGINAL: Trigger system notification
    """
    title = "Time to Review!"
    message = f"Concept: {concept}\nMemory Score: {memory_score:.2f}"
    try:
        notification.notify(title=title, message=message, timeout=5)
    except Exception as e:
        logger.error(f"Original notification failed: {e}")

# Example usage
if __name__ == "__main__":
    import networkx as nx
    from datetime import datetime, timedelta
    
    # Test original system
    G = nx.Graph()
    G.add_node("Photosynthesis", memory_score=0.5, next_review_time=datetime.now() - timedelta(minutes=1))
    
    print("Testing original reminder system:")
    check_reminders(G)
    
    # Test enhanced system
    G_enhanced = nx.Graph()
    G_enhanced.add_node("Mitochondria", 
                       memory_score=0.4, 
                       next_review_time=datetime.now() - timedelta(hours=2),
                       count=5)
    
    context = {
        'interaction_rate': 8,
        'app_type': 'browser',
        'intent_label': 'studying'
    }
    
    print("\nTesting enhanced reminder system:")
    reminders_sent = check_reminders_enhanced(G_enhanced, context)
    print(f"Reminders sent: {reminders_sent}")
    
    # Test analytics
    analytics = get_reminder_analytics()
    print("Reminder Analytics:", analytics)