from config import DB_PATH
import logging
import sys
import os

# Add core directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fkt.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def show_welcome_banner():
    """Display welcome banner with system information"""
    print("="*60)
    print("           FORGOTTEN KNOWLEDGE TRACKER")
    print("="*60)
    print("An AI-powered learning companion that helps you")
    print("remember what you learn using spaced repetition")
    print("="*60)
    print(f"Database path: {DB_PATH}")
    print("="*60)

def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    
    try:
        import sqlite3
    except ImportError:
        missing_deps.append("sqlite3")
    
    try:
        import numpy as np
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        import networkx as nx
    except ImportError:
        missing_deps.append("networkx")
    
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        missing_deps.append("sentence-transformers")
    
    try:
        import streamlit as st
    except ImportError:
        missing_deps.append("streamlit")
    
    if missing_deps:
        print("⚠️  Missing dependencies:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\nPlease install missing dependencies:")
        print("pip install " + " ".join(missing_deps))
        return False
    
    print("✅ All dependencies available")
    return True

def initialize_system():
    """Initialize the system and check readiness"""
    from core.db_module import init_db
    from core.knowledge_graph import sync_db_to_graph
    
    try:
        # Initialize database
        init_db()
        print("✅ Database initialized")
        
        # Sync knowledge graph
        sync_db_to_graph()
        print("✅ Knowledge graph synced")
        
        return True
    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        return False

def run_tracker():
    """Run the main tracker in enhanced mode"""
    from core.tracker import track_loop_enhanced, ask_user_permissions
    
    print("\nStarting Enhanced Tracker Mode...")
    print("This mode includes:")
    print("  - Privacy controls and consent management")
    print("  - SM-2 spaced repetition scheduling")
    print("  - Enhanced multi-modal context awareness")
    print("  - Adaptive reminder system")
    
    if ask_user_permissions():
        try:
            track_loop_enhanced()
        except KeyboardInterrupt:
            print("\nTracker stopped by user")
        except Exception as e:
            logger.error(f"Tracker error: {e}")
            print(f"Tracker error: {e}")

def run_dashboard():
    """Run the Streamlit dashboard"""
    import subprocess
    import webbrowser
    import time
    import threading
    
    print("\nStarting Dashboard...")
    print("The dashboard will open in your web browser")
    print("You can access it at: http://localhost:8501")
    
    def open_browser():
        time.sleep(3)  # Wait for server to start
        webbrowser.open("http://localhost:8501")
    
    # Start browser in background thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run Streamlit dashboard
    try:
        dashboard_path = os.path.join(os.path.dirname(__file__), 'dashboard.py')
        subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        print(f"Dashboard error: {e}")

def run_original_mode():
    """Run the original tracker mode for backward compatibility"""
    from core.tracker import track_loop, ask_user_permissions
    
    print("\nStarting Original Tracker Mode...")
    print("This mode uses the original algorithms without enhancements")
    
    ask_user_permissions()
    try:
        track_loop()
    except KeyboardInterrupt:
        print("\nTracker stopped by user")
    except Exception as e:
        logger.error(f"Original tracker error: {e}")

def main():
    """Main entry point with enhanced menu system"""
    show_welcome_banner()
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Please install missing dependencies before continuing")
        return
    
    # Initialize system
    if not initialize_system():
        print("❌ System initialization failed")
        return
    
    # Main menu
    while True:
        print("\n" + "="*40)
        print("MAIN MENU")
        print("="*40)
        print("1. 🚀 Run Enhanced Tracker (Recommended)")
        print("2. 📊 Open Dashboard Only")
        print("3. 🔄 Run Tracker + Dashboard Together")
        print("4. ⚡ Run Original Tracker Mode")
        print("5. 🔧 System Information")
        print("6. ❌ Exit")
        print("="*40)
        
        choice = input("Select option (1-6): ").strip()
        
        if choice == "1":
            run_tracker()
        elif choice == "2":
            run_dashboard()
        elif choice == "3":
            print("This feature would run both tracker and dashboard simultaneously.")
            print("Implementation note: Run tracker in background thread and dashboard in main thread.")
            # For now, suggest running separately
            print("Please run tracker and dashboard separately for now.")
        elif choice == "4":
            run_original_mode()
        elif choice == "5":
            show_system_info()
        elif choice == "6":
            print("Thank you for using Forgotten Knowledge Tracker!")
            break
        else:
            print("Invalid option. Please choose 1-6.")

def show_system_info():
    """Display system information and status"""
    import sqlite3
    import networkx as nx
    from core.knowledge_graph import get_graph, get_graph_statistics
    
    print("\n" + "="*40)
    print("SYSTEM INFORMATION")
    print("="*40)
    
    # Database information
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Session count
        c.execute("SELECT COUNT(*) FROM sessions")
        session_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM sessions_enhanced")
        enhanced_session_count = c.fetchone()[0]
        
        print(f"Sessions recorded: {session_count} (original), {enhanced_session_count} (enhanced)")
        
        # Latest session
        c.execute("SELECT start_ts, app_name FROM sessions ORDER BY start_ts DESC LIMIT 1")
        latest = c.fetchone()
        if latest:
            print(f"Latest session: {latest[1]} at {latest[0]}")
        
        conn.close()
    except Exception as e:
        print(f"Database info error: {e}")
    
    # Knowledge graph information
    try:
        G = get_graph()
        stats = get_graph_statistics()
        print(f"Concepts in graph: {stats['node_count']}")
        print(f"Average memory score: {stats['avg_memory_score']:.2f}")
        print(f"Concepts due for review: {stats['concepts_due_review']}")
    except Exception as e:
        print(f"Graph info error: {e}")
    
    # Configuration status
    from config import OCR_ENABLED, AUDIO_ENABLED, WEBCAM_ENABLED, RETENTION_DAYS
    print(f"\nModule Status:")
    print(f"  OCR: {'✅ Enabled' if OCR_ENABLED else '❌ Disabled'}")
    print(f"  Audio: {'✅ Enabled' if AUDIO_ENABLED else '❌ Disabled'}")
    print(f"  Webcam: {'✅ Enabled' if WEBCAM_ENABLED else '❌ Disabled'}")
    print(f"Data Retention: {RETENTION_DAYS} days")
    
    print("="*40)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nApplication interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Application error: {e}")