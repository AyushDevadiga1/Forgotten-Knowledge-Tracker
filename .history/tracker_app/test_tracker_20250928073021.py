# run_tracker.py - PROPER ENTRY POINT

import sys
import os

def setup_paths():
    """Set up Python paths correctly"""
    # Get current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    core_dir = os.path.join(current_dir, 'core')
    
    # Add to Python path
    sys.path.insert(0, current_dir)
    sys.path.insert(0, core_dir)
    
    print(f"Working directory: {current_dir}")
    print(f"Core directory: {core_dir}")
    
    # Verify core directory exists
    if not os.path.exists(core_dir):
        print(f"❌ ERROR: Core directory not found: {core_dir}")
        return False
    
    return True

def main():
    """Main entry point"""
    print("🚀 Starting Forgotten Knowledge Tracker")
    print("=" * 50)
    
    if not setup_paths():
        print("❌ Path setup failed")
        return
    
    try:
        # Import and run the tracker
        from core.tracker import KnowledgeTracker, ask_user_permissions
        
        print("✓ Modules imported successfully")
        print(f"✓ Starting tracker...")
        
        if ask_user_permissions():
            tracker = KnowledgeTracker()
            tracker.run()
        else:
            print("Tracker setup cancelled.")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure all module files exist in core/ directory")
        print("2. Check that core/__init__.py exists")
        print("3. Verify config.py has all required constants")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()