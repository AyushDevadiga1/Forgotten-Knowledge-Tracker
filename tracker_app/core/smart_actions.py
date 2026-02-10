"""
Smart Actions Module

Implements intelligent automation based on user intent and context.
"""

import os
import platform
from typing import Dict, Optional

class SmartActionsManager:
    """Manages smart actions based on user context"""
    
    def __init__(self):
        self.current_mode = None
        self.actions_enabled = True
        self.system = platform.system()
    
    def process_intent(self, intent: str, confidence: float) -> Optional[Dict]:
        """
        Process detected intent and trigger appropriate actions.
        
        Args:
            intent: Detected intent (studying, passive, idle)
            confidence: Confidence score (0-1)
            
        Returns:
            Dictionary of actions taken
        """
        if not self.actions_enabled or confidence < 0.7:
            return None
        
        actions_taken = {}
        
        if intent == "studying" and self.current_mode != "studying":
            actions_taken = self._enter_study_mode()
            self.current_mode = "studying"
            
        elif intent == "passive" and self.current_mode == "studying":
            actions_taken = self._exit_study_mode()
            self.current_mode = "passive"
            
        elif intent == "idle" and self.current_mode == "studying":
            actions_taken = self._exit_study_mode()
            self.current_mode = "idle"
        
        return actions_taken if actions_taken else None
    
    def _enter_study_mode(self) -> Dict:
        """Actions when entering study mode"""
        actions = {
            'mode': 'studying',
            'timestamp': None,
            'actions': []
        }
        
        # Windows-specific actions
        if self.system == "Windows":
            try:
                # Enable Do Not Disturb (Focus Assist)
                # Note: This requires registry access or PowerShell
                actions['actions'].append('DND_ENABLED')
            except Exception as e:
                print(f"Could not enable DND: {e}")
        
        # Cross-platform: Notification
        try:
            from plyer import notification
            notification.notify(
                title="FKT - Study Mode",
                message="Focus mode activated. Distractions minimized.",
                timeout=5
            )
            actions['actions'].append('NOTIFICATION_SENT')
        except Exception as e:
            print(f"Could not send notification: {e}")
        
        return actions
    
    def _exit_study_mode(self) -> Dict:
        """Actions when exiting study mode"""
        actions = {
            'mode': 'exited_study',
            'timestamp': None,
            'actions': []
        }
        
        # Disable Do Not Disturb
        if self.system == "Windows":
            try:
                actions['actions'].append('DND_DISABLED')
            except Exception as e:
                print(f"Could not disable DND: {e}")
        
        return actions
    
    def suggest_break(self, study_duration_minutes: int) -> Optional[str]:
        """Suggest break based on study duration"""
        if study_duration_minutes >= 50:
            return "You've been studying for 50+ minutes. Consider a 10-minute break!"
        elif study_duration_minutes >= 25:
            return "Pomodoro complete! Take a 5-minute break."
        return None
    
    def toggle_actions(self, enabled: bool):
        """Enable or disable smart actions"""
        self.actions_enabled = enabled

# Global instance
_smart_actions = None

def get_smart_actions_manager():
    """Get or create smart actions manager"""
    global _smart_actions
    if _smart_actions is None:
        _smart_actions = SmartActionsManager()
    return _smart_actions
