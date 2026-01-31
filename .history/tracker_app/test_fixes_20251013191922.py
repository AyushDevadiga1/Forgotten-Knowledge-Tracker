# core/tracker_debug.py - UPDATED VERSION
import time
import threading
from pynput import keyboard, mouse

class InputTester:
    def __init__(self):
        self.key_count = 0
        self.mouse_count = 0
        self.running = True
        
    def on_key_press(self, key):
        self.key_count += 1
        print(f"Key pressed: {key} (total: {self.key_count})")
    
    def on_mouse_click(self, x, y, button, pressed):
        if pressed:
            self.mouse_count += 1
            print(f"Mouse click: {button} (total: {self.mouse_count})")
    
    def start_test(self, duration=10):
        print(f"Input test starting for {duration} seconds...")
        print("Please click and type in the test window!")
        
        # Start listeners
        kb_listener = keyboard.Listener(on_press=self.on_key_press)
        ms_listener = mouse.Listener(on_click=self.on_mouse_click)
        kb_listener.start()
        ms_listener.start()
        
        # Countdown
        for i in range(duration, 0, -1):
            print(f"Time remaining: {i} seconds")
            time.sleep(1)
        
        # Stop listeners
        kb_listener.stop()
        ms_listener.stop()
        
        print(f"\nTest complete!")
        print(f"Keys pressed: {self.key_count}")
        print(f"Mouse clicks: {self.mouse_count}")
        print(f"Total events: {self.key_count + self.mouse_count}")

def debug_tracker():
    """Run tracker with enhanced debugging"""
    print("=== FORGOTTEN KNOWLEDGE TRACKER DEBUG MODE ===")
    
    # Test input listeners
    print("\n1. Testing input listeners...")
    tester = InputTester()
    tester.start_test(10)
    
    # Test other components
    print("\n2. Testing other components...")
    from core.tracker import get_active_window
    from core.db_module import init_all_databases
    
    window, rate = get_active_window()
    print(f"Active window: {window}")
    print(f"Interaction rate: {rate}")
    
    print("\n3. Testing database...")
    init_all_databases()
    print("Database initialized successfully")
    
    print("\n4. Starting main tracker...")
    print("Press Ctrl+C to stop tracking")
    
    # Start the main tracker
    from core.tracker import track_loop
    from threading import Event
    
    stop_event = Event()
    try:
        track_loop(stop_event)
    except KeyboardInterrupt:
        print("\nTracker stopped by user")
    except Exception as e:
        print(f"Tracker error: {e}")

if __name__ == "__main__":
    debug_tracker()