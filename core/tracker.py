# Phase 1: active window + interaction tracking
import time
import sqlite3
import psutil
from win32 import win32gui,win32process
from config import DB_PATH, WINDOW_POLL_INTERVAL

def get_active_window():
    hwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    process = psutil.Process(pid)
    app_name = process.name()
    window_title = win32gui.GetWindowText(hwnd)
    return app_name, window_title

def log_session(app_name, window_title):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sessions (start_ts, end_ts, app_name, window_title, interaction_rate) VALUES (datetime('now'), NULL, ?, ?, 0)",
        (app_name, window_title)
    )
    conn.commit()
    conn.close()

def start_tracking():
    print("Tracking started...")
    last_app = None
    while True:
        try:
            app_name, window_title = get_active_window()
            if app_name != last_app:
                log_session(app_name, window_title)
                print(f"[LOG] New session: {app_name} - {window_title}")
                last_app = app_name
        except Exception as e:
            print("Error:", e)
        time.sleep(WINDOW_POLL_INTERVAL)
