from core.tracker import track_loop, ask_user_permissions

if __name__ == "__main__":
    print("Forgotten Knowledge Tracker initializing...")
    allow_webcam = ask_user_permissions()
    track_loop(webcam_enabled=allow_webcam)
