"""
Adaptive Monitoring System

Adjusts monitoring intervals based on user activity and context.
"""

import time
from datetime import datetime, timedelta
from typing import Optional

class AdaptiveMonitor:
    """Manages dynamic monitoring intervals based on activity"""
    
    def __init__(self):
        self.last_activity_time = time.time()
        self.last_screen_change_time = time.time()
        self.activity_count = 0
        self.idle_threshold_seconds = 300  # 5 minutes
        self.high_activity_threshold = 10  # interactions per minute
        
        # Interval configurations (in seconds)
        self.intervals = {
            'idle': 300,        # 5 minutes when idle
            'low_activity': 60,  # 1 minute for low activity
            'normal': 20,        # 20 seconds normal
            'high_activity': 10  # 10 seconds when very active
        }
        
        self.current_mode = 'normal'
    
    def record_activity(self):
        """Record user activity (keyboard/mouse)"""
        self.last_activity_time = time.time()
        self.activity_count += 1
    
    def record_screen_change(self):
        """Record screen content change"""
        self.last_screen_change_time = time.time()
    
    def get_idle_duration(self) -> float:
        """Get seconds since last activity"""
        return time.time() - self.last_activity_time
    
    def is_idle(self) -> bool:
        """Check if user is idle"""
        return self.get_idle_duration() > self.idle_threshold_seconds
    
    def get_activity_rate(self) -> float:
        """Get activity rate (interactions per minute)"""
        # Calculate over last minute
        return self.activity_count  # Simplified
    
    def get_current_interval(self) -> int:
        """Get appropriate monitoring interval based on current state"""
        if self.is_idle():
            self.current_mode = 'idle'
            return self.intervals['idle']
        
        activity_rate = self.get_activity_rate()
        
        if activity_rate > self.high_activity_threshold:
            self.current_mode = 'high_activity'
            return self.intervals['high_activity']
        elif activity_rate > 5:
            self.current_mode = 'normal'
            return self.intervals['normal']
        else:
            self.current_mode = 'low_activity'
            return self.intervals['low_activity']
    
    def reset_activity_counter(self):
        """Reset activity counter (call every minute)"""
        self.activity_count = 0
    
    def should_capture_now(self, last_capture_time: float) -> bool:
        """Determine if we should capture now based on adaptive logic"""
        elapsed = time.time() - last_capture_time
        current_interval = self.get_current_interval()
        return elapsed >= current_interval
    
    def get_status(self) -> dict:
        """Get current monitoring status"""
        return {
            'mode': self.current_mode,
            'interval': self.get_current_interval(),
            'idle_duration': self.get_idle_duration(),
            'is_idle': self.is_idle(),
            'activity_rate': self.get_activity_rate()
        }

# Global instance
_adaptive_monitor = None

def get_adaptive_monitor():
    """Get or create adaptive monitor instance"""
    global _adaptive_monitor
    if _adaptive_monitor is None:
        _adaptive_monitor = AdaptiveMonitor()
    return _adaptive_monitor
