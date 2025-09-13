#!/usr/bin/env python3
import sys
import os
import time

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.reminder_system import ReminderSystem
from core.forgetting_curve import ForgettingCurve
from core.database import DatabaseManager

def test_reminder_system():
    print("🔔 Testing Reminder System")
    print("==========================")
    
    # Initialize components
    db = DatabaseManager(":memory:")  # Use in-memory DB for testing
    curve = ForgettingCurve()
    reminder = ReminderSystem(db, curve)
    
    print("1. Testing notification creation...")
    
    # Create test knowledge item that should need review
    test_item = {
        'type': 'window',
        'title': 'Python Machine Learning Tutorial',
        'app': 'vscode.exe',
        'timestamp': '2024-01-01T10:00:00',  # Very old date
        'duration': 300,
        'is_educational': True
    }
    
    # Manually test notification
    suggestion = {
        'item': test_item,
        'retention_score': 0.15,  # Low retention = needs review
        'review_time': '2024-01-10T10:00:00',
        'urgency': 0.85
    }
    
    print("2. Testing console notification fallback...")
    reminder._send_console_notification(suggestion, 1)
    
    print("3. Testing message creation...")
    message = reminder._create_notification_message(test_item, 0.15)
    print(f"   Notification message: {message}")
    
    print("4. Testing knowledge items retrieval...")
    items = reminder._get_knowledge_items()
    print(f"   Found {len(items)} knowledge items")
    
    print("==========================")
    print("🎉 Reminder system ready!")
    print("Next: Integrate with main app controller")

if __name__ == "__main__":
    test_reminder_system()