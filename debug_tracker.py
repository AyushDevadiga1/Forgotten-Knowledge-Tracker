#!/usr/bin/env python3
"""
Simple debug script to test the TabTracker module manually
"""
import time
import logging
from core.tracker import TabTracker

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    print("🔍 Testing Tab Tracker Module...")
    print("=" * 50)
    
    # Initialize the tracker with shorter interval for testing
    tracker = TabTracker(update_interval=1)  # 1-second intervals
    
    print("1. Testing window info detection...")
    window_info = tracker.get_active_window_info()
    print(f"   Current window: {window_info}")
    
    print("\n2. Starting tracking for 8 seconds...")
    tracker.start_tracking()
    
    # Let it run for a bit - try switching windows during this time
    print("   Tracking active windows. Please switch between some applications...")
    print("   (Try opening Browser, File Explorer, different apps)")
    for i in range(8):
        time.sleep(1)
        if i % 2 == 0:
            print(f"   ...{8 - i} seconds remaining")
    
    print("\n3. Stopping tracking...")
    tracker.stop_tracking()
    
    print("\n4. Displaying captured history:")
    history = tracker.get_history()
    stats = tracker.get_stats()
    
    print(f"   Total tracking time: {stats['total_time']} seconds")
    print(f"   Number of window entries: {stats['total_entries']}")
    print(f"   Unique applications: {stats['unique_apps']}")
    print("\n   Detailed history:")
    print("   " + "-" * 60)
    
    if history:
        for i, entry in enumerate(history):
            app_display = entry['app'] if entry['app'] != "Unknown App" else "System App"
            title_display = entry['title'][:50] + "..." if len(entry['title']) > 50 else entry['title']
            print(f"   {i+1:2d}. {app_display:15} - {title_display:50} ({entry['duration']:2d}s)")
    else:
        print("   ❌ No window history captured.")
    
    print("\n✅ Debug test completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()