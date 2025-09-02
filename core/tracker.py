import time
import threading
from datetime import datetime
from pywinctl import getActiveWindow
import logging
from .database import DatabaseManager

logger = logging.getLogger(__name__)

class TabTracker:
    def __init__(self, update_interval=5, db_path="data/tracking.db"):
        self.update_interval = update_interval
        self.current_window = None
        self.window_history = []
        self.is_tracking = False
        self.tracking_thread = None
        self.last_valid_window = None
        
        # Initialize database manager
        self.db_manager = DatabaseManager(db_path)
    
    def get_active_window(self):
        """Get the currently active window with error handling"""
        try:
            window = getActiveWindow()
            return window if window else None
        except Exception as e:
            logger.error(f"Error getting active window: {e}")
            return None
    
    def get_current_window_info(self):
        """Get information about the currently active window"""
        try:
            active_window = self.get_active_window()
            if active_window:
                return {
                    'title': active_window.title,
                    'app': self._get_app_name(active_window),
                    'timestamp': datetime.now().isoformat()
                }
            return {'title': 'Unknown', 'app': 'Unknown', 'timestamp': datetime.now().isoformat()}
        except Exception as e:
            logger.error(f"Error getting current window info: {e}")
            return {'title': 'Error', 'app': 'Error', 'timestamp': datetime.now().isoformat()}
    
    def get_active_window_info(self):
        """Get information about the active window"""
        try:
            window = self.get_active_window()
            if not window:
                return None
                
            title = window.title if hasattr(window, 'title') else "Unknown"
            app_name = self._get_app_name(window)
            
            return {
                'title': title,
                'app': app_name,
                'timestamp': datetime.now().isoformat(),
                'duration': self.update_interval
            }
        except Exception as e:
            logger.error(f"Error getting window info: {e}")
            return None

    def _get_app_name(self, window):
        """Get application name from window object with robust error handling"""
        try:
            # Try to get app name using different methods
            if hasattr(window, 'getAppName') and callable(window.getAppName):
                return window.getAppName()
            elif hasattr(window, 'appName') and window.appName:
                return window.appName
            elif hasattr(window, 'processId'):
                # Fallback: try to get process name from PID
                try:
                    import psutil
                    process = psutil.Process(window.processId)
                    return process.name()
                except (ImportError, psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Final fallback: extract from window title or return generic name
            title = window.title if hasattr(window, 'title') else str(window)
            if " - " in title:
                return title.split(" - ")[-1]
            elif ":" in title:
                return title.split(":")[0]
            else:
                return "Unknown Application"
                
        except Exception as e:
            # Don't log the error to avoid spam, just return a generic name
            return "Unknown Application"
    
    def update_window_history(self):
        """Update the window history with current active window"""
        window_info = self.get_active_window_info()
        
        if not window_info:
            return
            
        # Store the current window for reference
        self.current_window = window_info
        
        # If same window as before, update duration
        if (self.window_history and 
            self.window_history[-1]['title'] == window_info['title'] and
            self.window_history[-1]['app'] == window_info['app']):
            self.window_history[-1]['duration'] += self.update_interval
        else:
            # Add new entry and save to database
            self.window_history.append(window_info)
            # Save to database immediately
            self.db_manager.save_window_entry(window_info)
    
    def tracking_loop(self):
        """Main tracking loop with error handling"""
        while self.is_tracking:
            try:
                self.update_window_history()
            except Exception as e:
                logger.error(f"Error in tracking loop: {e}")
            time.sleep(self.update_interval)
    
    def start_tracking(self):
        """Start tracking windows"""
        if self.is_tracking:
            logger.info("Tracking is already running")
            return False
            
        self.is_tracking = True
        self.tracking_thread = threading.Thread(target=self.tracking_loop)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        logger.info("Window tracking started")
        return True
    
    def stop_tracking(self):
        """Stop tracking windows"""
        if not self.is_tracking:
            logger.info("Tracking is not running")
            return False
            
        self.is_tracking = False
        if self.tracking_thread:
            self.tracking_thread.join(timeout=1.0)
        logger.info("Window tracking stopped")
        return True
    
    def get_history(self, from_db=False, limit=100):
        """Get window history - either from memory or database"""
        if from_db:
            return self.db_manager.get_recent_history(limit)
        return self.window_history.copy()
    
    def clear_history(self, clear_db=False):
        """Clear window history - optionally from database too"""
        self.window_history = []
        logger.info("Window history cleared" + (" from memory" if not clear_db else " from memory and database"))
    
    def get_stats(self):
        """Get statistics about the tracking session"""
        if not self.window_history:
            return {"total_entries": 0, "total_time": 0, "unique_apps": 0}
        
        total_time = sum(entry['duration'] for entry in self.window_history)
        unique_apps = len(set(entry['app'] for entry in self.window_history))
        
        return {
            "total_entries": len(self.window_history),
            "total_time": total_time,
            "unique_apps": unique_apps,
            "is_tracking": self.is_tracking
        }