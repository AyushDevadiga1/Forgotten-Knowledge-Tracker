#!/usr/bin/env python3
import time
import sys
import os

# Add the current directory to Python path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.app_controller import AppController

def main():
    print("🚀 Starting Forgotten Knowledge Tracker...")
    
    # Initialize controller with 30-second screenshot interval
    controller = AppController(screenshot_interval=30)
    
    try:
        # Start tracking
        controller.start()
        
        print("\n📋 App is now running:")
        print("• Window tracking: Active")
        print("• Screenshot capture: Every 30 seconds")
        print("• OCR processing: Automatic")
        print("• Database storage: Active")
        print("\n⌨️  Press Ctrl+C to stop...")
        
        # Keep the program running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Shutting down...")
    finally:
        try:
            controller.stop()
            
            # Show final stats
            stats = controller.get_stats()
            print(f"\n📊 Final Statistics:")
            print(f"• Screenshots captured: {stats['screenshot_count']}")
            print(f"• OCR processes completed: {stats['ocr_processing_count']}")
            print(f"• Window tracking entries: {stats['window_stats']['total_entries']}")
            
        except Exception as e:
            print(f"Error getting final stats: {e}")

if __name__ == "__main__":
    main()