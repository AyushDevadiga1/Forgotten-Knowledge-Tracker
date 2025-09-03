#!/usr/bin/env python3
from core.database import DatabaseManager

def check_collected_data():
    db = DatabaseManager()
    
    # Get window tracking stats using existing methods
    window_count = len(db.get_recent_history(1000))  # Get all history
    total_time = db.get_total_tracking_time()
    
    # Get screenshot stats using existing methods
    screenshot_count = db.get_screenshot_count()
    ocr_count = db.get_ocr_result_count()
    
    print("📊 Data Collection Report")
    print("========================")
    print(f"Window history entries: {window_count}")
    print(f"Total tracking time: {total_time} seconds")
    print(f"Screenshots captured: {screenshot_count}")
    print(f"OCR results stored: {ocr_count}")
    
    # Show recent windows
    print("\nRecent window activity:")
    recent = db.get_recent_history(5)
    for i, window in enumerate(recent):
        print(f"  {i+1}. {window['app']} - {window['title'][:50]}...")
    
    # Show most used apps
    print("\nMost used applications:")
    apps = db.get_most_used_apps(3)
    for i, app in enumerate(apps):
        print(f"  {i+1}. {app['app']} - {app['total_time']} seconds")

if __name__ == "__main__":
    check_collected_data()