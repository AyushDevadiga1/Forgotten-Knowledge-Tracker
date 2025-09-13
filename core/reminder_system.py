import time
import threading
import schedule
import logging
from datetime import datetime
from plyer import notification

logger = logging.getLogger(__name__)

class ReminderSystem:
    def __init__(self, db_manager, forgetting_curve):
        self.db = db_manager
        self.curve = forgetting_curve
        self.is_running = False
        self.reminder_thread = None
        logger.info("Reminder system initialized")
    
    def check_for_reviews(self):
        """Check for knowledge items that need review"""
        try:
            logger.info("🔍 Checking for knowledge that needs review...")
            
            # Get knowledge items from database
            knowledge_items = self._get_knowledge_items()
            
            if not knowledge_items:
                logger.info("No knowledge items found for review check")
                return
            
            # Get review suggestions using forgetting curve
            review_suggestions = self.curve.get_review_suggestions(knowledge_items)
            
            if not review_suggestions:
                logger.info("No knowledge needs review at this time")
                return
            
            logger.info(f"Found {len(review_suggestions)} items needing review")
            
            # Send notifications for top items
            for i, suggestion in enumerate(review_suggestions[:3]):  # Limit to top 3
                self._send_review_notification(suggestion, i+1)
                
        except Exception as e:
            logger.error(f"Error in review check: {e}")
    
    def _get_knowledge_items(self, limit=100):
        """Get knowledge items from database for review consideration"""
        try:
            items = []
            
            # Get window history
            window_items = self.db.get_recent_history(limit)
            for item in window_items:
                items.append({
                    'type': 'window',
                    'title': item['title'],
                    'app': item['app'],
                    'timestamp': item['timestamp'],
                    'duration': item.get('duration', 0)
                })
            
            # Get audio recordings with transcripts
            audio_items = self.db.get_audio_recordings(limit)
            for item in audio_items:
                if item['transcribed_text'] and item['transcribed_text'].strip():
                    items.append({
                        'type': 'audio',
                        'title': f"Audio discussion about {item['keywords'][0] if item['keywords'] else 'unknown topic'}",
                        'content': item['transcribed_text'],
                        'timestamp': item['timestamp'],
                        'word_count': item.get('word_count', 0),
                        'is_educational': item.get('is_educational', False),
                        'keywords': item.get('keywords', [])
                    })
            
            logger.debug(f"Retrieved {len(items)} knowledge items for review consideration")
            return items
            
        except Exception as e:
            logger.error(f"Error getting knowledge items: {e}")
            return []
    
    def _send_review_notification(self, suggestion, priority=1):
        """Send desktop notification for review"""
        try:
            item = suggestion['item']
            retention = suggestion['retention_score']
            review_time = suggestion['review_time']
            
            title = f"🧠 Review Reminder ({priority})"
            message = self._create_notification_message(item, retention)
            
            # Send desktop notification
            notification.notify(
                title=title,
                message=message,
                timeout=15,  # Show for 15 seconds
                app_name="Forgotten Knowledge Tracker"
            )
            
            logger.info(f"📨 Sent review notification: {message[:50]}...")
            
        except Exception as e:
            # Fallback to console notification if desktop notifications fail
            logger.warning(f"Desktop notification failed: {e}")
            self._send_console_notification(suggestion, priority)
    
    def _create_notification_message(self, item, retention):
        """Create notification message based on item type"""
        item_type = item.get('type', 'unknown')
        title = item.get('title', 'Unknown content')
        
        if item_type == 'window':
            app = item.get('app', 'Unknown app')
            return f"Review {title} ({app}) - {retention:.1%} retained"
        
        elif item_type == 'audio':
            keywords = item.get('keywords', [])
            if keywords:
                return f"Review discussion about {keywords[0]} - {retention:.1%} retained"
            else:
                return f"Review previous discussion - {retention:.1%} retained"
        
        else:
            return f"Time to review: {title} - {retention:.1%} retained"
    
    def _send_console_notification(self, suggestion, priority):
        """Fallback: Send notification to console"""
        item = suggestion['item']
        retention = suggestion['retention_score']
        
        print(f"\n🔔 REMINDER #{priority}")
        print(f"   Content: {item.get('title', 'Unknown')}")
        print(f"   Retention: {retention:.1%}")
        print(f"   Type: {item.get('type', 'unknown')}")
        print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 50)
    
    def start_daily_checks(self, check_times=['09:00', '14:00', '19:00']):
        """Start scheduled daily review checks"""
        if self.is_running:
            logger.warning("Reminder system is already running")
            return
        
        self.is_running = True
        
        # Schedule checks at specified times
        for check_time in check_times:
            schedule.every().day.at(check_time).do(self.check_for_reviews)
            logger.info(f"📅 Scheduled daily check at {check_time}")
        
        def scheduler_loop():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        self.reminder_thread = threading.Thread(target=scheduler_loop)
        self.reminder_thread.daemon = True
        self.reminder_thread.start()
        
        logger.info("🚀 Reminder system started with scheduled checks")
    
    def stop(self):
        """Stop the reminder system"""
        self.is_running = False
        if self.reminder_thread:
            self.reminder_thread.join(timeout=5.0)
        logger.info("🛑 Reminder system stopped")

# Global instance (will be initialized in app controller)
reminder_system = None