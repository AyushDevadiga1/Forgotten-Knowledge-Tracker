#!/usr/bin/env python3
import sys
import os
import sqlite3
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import DatabaseManager
from datetime import datetime, timedelta

def show_dashboard():
    """Show knowledge tracking dashboard"""
    db = DatabaseManager()
    
    print("📊 Forgotten Knowledge Dashboard")
    print("================================")
    
    # Get statistics
    window_stats = db.get_most_used_apps(limit=5)
    total_time = db.get_total_tracking_time()
    screenshot_count = db.get_screenshot_count()
    ocr_count = db.get_ocr_result_count()
    audio_stats = db.get_audio_stats()
    
    # Convert seconds to hours/minutes
    hours = total_time // 3600
    minutes = (total_time % 3600) // 60
    
    print(f"\n⏰ Total Tracking Time: {hours}h {minutes}m")
    print(f"📸 Screenshots: {screenshot_count}")
    print(f"🔤 OCR Processes: {ocr_count}")
    print(f"🎤 Audio Recordings: {audio_stats.get('total_recordings', 0)}")
    print(f"🎧 Audio Duration: {audio_stats.get('total_duration_seconds', 0)}s")
    
    print(f"\n🏆 Top Applications:")
    print("=" * 40)
    for i, app in enumerate(window_stats, 1):
        app_time = app['total_time']
        app_hours = app_time // 3600
        app_minutes = (app_time % 3600) // 60
        print(f"{i}. {app['app']}: {app_hours}h {app_minutes}m ({app['usage_count']} sessions)")
    
    print(f"\n🔍 Recent Activity:")
    print("=" * 40)
    
    # Use the correct method name - let's try a few possibilities
    try:
        # Try different possible method names
        if hasattr(db, 'get_recent_history'):
            recent_entries = db.get_recent_history(limit=3)
        elif hasattr(db, 'get_recent_entries'):
            recent_entries = db.get_recent_entries(limit=3) 
        else:
            # Fallback: get window history directly
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT title, app, start_time FROM window_history ORDER BY start_time DESC LIMIT 3')
            recent_entries = [{'title': row[0], 'app': row[1], 'timestamp': row[2]} for row in cursor.fetchall()]
            conn.close()
            
        for entry in recent_entries:
            time_str = entry['timestamp'].split('T')[1][:8] if 'T' in entry['timestamp'] else entry['timestamp'][11:19]
            print(f"⏰ {time_str} - {entry['app']}: {entry['title'][:50]}...")
            
    except Exception as e:
        print("📝 Recent activity display temporarily unavailable")
        print(f"   (Debug: {e})")

if __name__ == "__main__":
    show_dashboard()