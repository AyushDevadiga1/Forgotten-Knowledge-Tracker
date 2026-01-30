"""
Reminders and Notifications System
Manages study reminders, notifications, and scheduling
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os


class RemindersSystem:
    """Manages reminders and notifications for learning items"""

    def __init__(self, db_path: str = 'learning_tracker.db'):
        self.db_path = db_path
        self._initialize_reminders_table()

    def _initialize_reminders_table(self):
        """Create reminders table if it doesn't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    reminder_type TEXT NOT NULL,
                    reminder_time TEXT NOT NULL,
                    frequency TEXT DEFAULT 'once',
                    is_active BOOLEAN DEFAULT 1,
                    created_date TEXT NOT NULL,
                    last_sent TEXT,
                    FOREIGN KEY (item_id) REFERENCES learning_items(item_id)
                )
            ''')
            conn.commit()

    def create_reminder(self, item_id: int, reminder_type: str = 'due_review',
                       frequency: str = 'once') -> int:
        """
        Create a new reminder for an item
        
        Args:
            item_id: Item to remind about
            reminder_type: 'due_review', 'weekly_check', 'struggling'
            frequency: 'once', 'daily', 'weekly'
        
        Returns:
            Reminder ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get item's next review date
            cursor.execute('SELECT next_review_date FROM learning_items WHERE item_id = ?',
                          (item_id,))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError(f"Item {item_id} not found")
            
            next_review = result[0]
            reminder_time = next_review if reminder_type == 'due_review' else datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO reminders (item_id, reminder_type, reminder_time, frequency, created_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (item_id, reminder_type, reminder_time, frequency, datetime.now().isoformat()))
            
            conn.commit()
            return cursor.lastrowid

    def get_active_reminders(self) -> List[Dict]:
        """Get all active reminders"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    r.reminder_id,
                    r.item_id,
                    li.question,
                    r.reminder_type,
                    r.reminder_time,
                    r.frequency
                FROM reminders r
                JOIN learning_items li ON r.item_id = li.item_id
                WHERE r.is_active = 1
                ORDER BY r.reminder_time
            ''')
            
            return [{
                'reminder_id': row[0],
                'item_id': row[1],
                'question': row[2][:50] + '...' if len(row[2]) > 50 else row[2],
                'type': row[3],
                'time': row[4],
                'frequency': row[5]
            } for row in cursor.fetchall()]

    def get_due_reminders(self) -> List[Dict]:
        """Get reminders that are due now"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute('''
                SELECT 
                    r.reminder_id,
                    r.item_id,
                    li.question,
                    r.reminder_type,
                    li.difficulty
                FROM reminders r
                JOIN learning_items li ON r.item_id = li.item_id
                WHERE r.is_active = 1
                    AND r.reminder_time <= ?
                    AND (r.last_sent IS NULL OR datetime(r.last_sent) < datetime('now', '-1 day'))
                ORDER BY r.reminder_time
            ''', (now,))
            
            due = [{
                'reminder_id': row[0],
                'item_id': row[1],
                'question': row[2],
                'type': row[3],
                'difficulty': row[4]
            } for row in cursor.fetchall()]
            
            # Update last_sent
            for reminder in due:
                cursor.execute('''
                    UPDATE reminders 
                    SET last_sent = ?
                    WHERE reminder_id = ?
                ''', (datetime.now().isoformat(), reminder['reminder_id']))
            
            conn.commit()
            return due

    def mark_reminder_complete(self, reminder_id: int):
        """Mark reminder as complete"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE reminders
                SET is_active = 0
                WHERE reminder_id = ?
            ''', (reminder_id,))
            conn.commit()

    def snooze_reminder(self, reminder_id: int, minutes: int = 60):
        """Snooze a reminder"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT reminder_time FROM reminders WHERE reminder_id = ?',
                          (reminder_id,))
            result = cursor.fetchone()
            
            if result:
                current_time = datetime.fromisoformat(result[0])
                new_time = current_time + timedelta(minutes=minutes)
                
                cursor.execute('''
                    UPDATE reminders
                    SET reminder_time = ?
                    WHERE reminder_id = ?
                ''', (new_time.isoformat(), reminder_id))
                
                conn.commit()


class NotificationCenter:
    """Central notification management"""

    def __init__(self, db_path: str = 'learning_tracker.db'):
        self.db_path = db_path
        self.reminders = RemindersSystem(db_path)
        self._initialize_notifications_table()

    def _initialize_notifications_table(self):
        """Create notifications table"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    related_item_id INTEGER,
                    is_read BOOLEAN DEFAULT 0,
                    created_date TEXT NOT NULL,
                    action_data TEXT
                )
            ''')
            conn.commit()

    def create_notification(self, title: str, message: str, notification_type: str,
                          related_item_id: Optional[int] = None,
                          action_data: Optional[Dict] = None):
        """Create a new notification"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            action_json = json.dumps(action_data) if action_data else None
            
            cursor.execute('''
                INSERT INTO notifications (title, message, notification_type, related_item_id, created_date, action_data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, message, notification_type, related_item_id, 
                  datetime.now().isoformat(), action_json))
            
            conn.commit()
            return cursor.lastrowid

    def get_unread_notifications(self) -> List[Dict]:
        """Get all unread notifications"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    notification_id,
                    title,
                    message,
                    notification_type,
                    related_item_id,
                    created_date
                FROM notifications
                WHERE is_read = 0
                ORDER BY created_date DESC
            ''')
            
            return [{
                'id': row[0],
                'title': row[1],
                'message': row[2],
                'type': row[3],
                'item_id': row[4],
                'created': row[5]
            } for row in cursor.fetchall()]

    def mark_notification_read(self, notification_id: int):
        """Mark notification as read"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE notifications
                SET is_read = 1
                WHERE notification_id = ?
            ''', (notification_id,))
            conn.commit()

    def generate_study_notifications(self) -> List[Dict]:
        """Generate notifications based on study patterns"""
        notifications = []
        
        # Check for due items
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM learning_items
                WHERE next_review_date <= datetime('now')
            ''')
            
            due_count = cursor.fetchone()[0]
            
            if due_count > 0:
                notification = self.create_notification(
                    title='Study Session Ready',
                    message=f'You have {due_count} item{"s" if due_count != 1 else ""} due for review',
                    notification_type='due_items',
                    action_data={'items_due': due_count}
                )
                notifications.append({
                    'id': notification,
                    'title': 'Study Session Ready',
                    'message': f'You have {due_count} item{"s" if due_count != 1 else ""} due for review'
                })
            
            # Check for struggling items
            cursor.execute('''
                SELECT COUNT(DISTINCT li.item_id) FROM learning_items li
                JOIN review_history rh ON li.item_id = rh.item_id
                WHERE rh.review_date > datetime('now', '-7 days')
                GROUP BY li.item_id
                HAVING AVG(rh.quality_rating) < 3
            ''')
            
            struggling_count = cursor.fetchone()[0] if cursor.fetchone() else 0
            
            if struggling_count > 0:
                notification = self.create_notification(
                    title='Items Need Help',
                    message=f'{struggling_count} item{"s" if struggling_count != 1 else ""} need more practice',
                    notification_type='struggling_items',
                    action_data={'items_struggling': struggling_count}
                )
                notifications.append({
                    'id': notification,
                    'title': 'Items Need Help',
                    'message': f'{struggling_count} item{"s" if struggling_count != 1 else ""} need more practice'
                })
        
        return notifications

    def get_notification_summary(self) -> Dict:
        """Get notification summary"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM notifications WHERE is_read = 0')
            unread_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM reminders WHERE is_active = 1')
            active_reminders = cursor.fetchone()[0]
            
            return {
                'unread_notifications': unread_count,
                'active_reminders': active_reminders,
                'has_alerts': unread_count > 0 or active_reminders > 0
            }
