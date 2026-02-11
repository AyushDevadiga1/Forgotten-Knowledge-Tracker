"""
ROI (Region of Interest) Detection for Active Window

Captures only the active window instead of full screen for better performance.
"""

import win32gui
import win32ui
import win32con
from ctypes import windll
import numpy as np
import cv2

def get_active_window_rect():
    """Get the bounding rectangle of the active window"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            rect = win32gui.GetWindowRect(hwnd)
            # rect is (left, top, right, bottom)
            return {
                'hwnd': hwnd,
                'left': rect[0],
                'top': rect[1],
                'width': rect[2] - rect[0],
                'height': rect[3] - rect[1],
                'title': win32gui.GetWindowText(hwnd)
            }
    except Exception as e:
        print(f"Error getting active window: {e}")
    return None

def capture_active_window():
    """Capture screenshot of only the active window (ROI)"""
    try:
        window_info = get_active_window_rect()
        if not window_info:
            return None, None
        
        hwnd = window_info['hwnd']
        width = window_info['width']
        height = window_info['height']
        
        # Validate window still exists
        if not win32gui.IsWindow(hwnd):
            return None, None
        
        # Skip if window is too small (likely a popup or notification)
        if width < 100 or height < 50:
            return None, None
        
        # Skip if window is minimized
        if win32gui.IsIconic(hwnd):
            return None, None
        
        # Get window DC
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        
        # Create bitmap
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        
        # Copy window content
        result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
        
        # Convert to numpy array
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img = np.frombuffer(bmpstr, dtype=np.uint8)
        img.shape = (height, width, 4)
        
        # Cleanup
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        
        if result == 1:
            # Convert BGRA to BGR
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img, window_info
        
        return None, None
        
    except Exception as e:
        print(f"Error capturing active window: {e}")
        return None, None

def should_skip_window(window_title):
    """Check if window should be skipped for privacy/relevance"""
    skip_patterns = [
        'password', 'login', 'sign in', 'authentication',
        'private', 'incognito', 'inprivate',
        'task manager', 'settings', 'control panel'
    ]
    
    title_lower = window_title.lower()
    return any(pattern in title_lower for pattern in skip_patterns)
