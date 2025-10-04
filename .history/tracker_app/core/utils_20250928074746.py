# core/utils.py - SHARED UTILITIES

import win32gui

def get_active_window():
    """Shared window detection function"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        return title
    except Exception as e:
        print(f"Window detection error: {e}")
        return "Unknown"

def classify_app_type(window_title):
    """Shared app classification"""
    if not window_title:
        return "unknown"
    
    title_lower = window_title.lower()
    
    study_keywords = ["chrome", "firefox", "edge", "browser", "word", "pdf", "notepad",
                     "visual studio", "pycharm", "vscode", "jupyter", "anaconda"]
    
    entertainment_keywords = ["youtube", "netflix", "spotify", "game", "steam", "twitch"]
    
    if any(keyword in title_lower for keyword in study_keywords):
        return "study"
    elif any(keyword in title_lower for keyword in entertainment_keywords):
        return "entertainment"
    elif "calculator" in title_lower or "cmd" in title_lower or "terminal" in title_lower:
        return "utility"
    else:
        return "other"

def get_interaction_rate():
    """Get interaction rate (if available)"""
    # This would need to be implemented based on your tracking system
    return 0