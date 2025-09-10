#!/usr/bin/env python3
import time
import sys
import os

# Add the current directory to Python path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.app_controller import AppController

def main():
    print("🚀 Starting Forgotten Knowledge Tracker...")
    print("📊 Phase 3: Audio Monitoring Enabled")
    
    # Initialize controller with audio monitoring every 5 minutes
    controller = AppController(
        screenshot_interval=30,    # Capture screenshots every 30 seconds
        audio_interval=300         # Capture audio every 5 minutes
    )
    
    try:
        # Start tracking (includes audio now)
        controller.start()
        
        print("\n📋 App is now running:")
        print("• Window tracking: Active")
        print("• Screenshot capture: Every 30 seconds")
        print("• Audio monitoring: Every 5 minutes")#We have to delete tracking after each phase as it will compare data from new trackin each time
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
            print(f"• Audio recordings: {stats['audio_stats'].get('total_recordings', 0)}")
            print(f"• Audio duration: {stats['audio_stats'].get('total_duration_seconds', 0)} seconds")
            
        except Exception as e:
            print(f"Error getting final stats: {e}")

if __name__ == "__main__":
    main()