# core/tracker_debug.py
import time
from core.tracker import track_loop, ThreadSafeCounter, start_listeners, get_active_window
from core.db_module import init_all_databases
from threading import Event

def debug_tracker():
    """Run tracker with enhanced debugging"""
    print("=== FORGOTTEN KNOWLEDGE TRACKER DEBUG MODE ===")
    
    # Test individual components first
    print("\n1. Testing input listeners...")
    keyboard_counter = ThreadSafeCounter()
    mouse_counter = ThreadSafeCounter()
    
    def test_key_press(key):
        keyboard_counter.increment()
        print(f"Key pressed: {key}")
    
    def test_mouse_click(x, y, button, pressed):
        if pressed:
            mouse_counter.increment()
            print(f"Mouse click: {button} at ({x}, {y})")
    
    # Start test listeners
    from pynput import keyboard, mouse
    kb_listener = keyboard.Listener(on_press=test_key_press)
    ms_listener = mouse.Listener(on_click=test_mouse_click)
    kb_listener.start()
    ms_listener.start()
    
    print("Input listeners started. Press some keys and click mouse to test...")
    time.sleep(5)
    
    kb_listener.stop()
    ms_listener.stop()
    print(f"Test results - Keys: {keyboard_counter.get_value()}, Clicks: {mouse_counter.get_value()}")
    
    print("\n2. Testing active window detection...")
    window, rate = get_active_window()
    print(f"Active window: {window}")
    print(f"Interaction rate: {rate}")
    
    print("\n3. Testing database...")
    init_all_databases()
    print("Database initialized successfully")
    
    print("\n4. Starting main tracker...")
    print("Press Ctrl+C to stop tracking")
    
    # Start the main tracker
    stop_event = Event()
    try:
        track_loop(stop_event)
    except KeyboardInterrupt:
        print("\nTracker stopped by user")
    except Exception as e: coding in here what to do i dont know 
        print(f"Tracker error: {e}")

if __name__ == "__main__":
    debug_tracker()