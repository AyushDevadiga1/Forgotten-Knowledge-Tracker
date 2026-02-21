from tracker_app.core.tracker import track_loop, ask_user_permissions
from tracker_app.config import setup_directories

if __name__ == "__main__":
    setup_directories()  # Ensure data/ and models/ dirs exist before tracker starts
    print("Forgotten Knowledge Tracker initializing...")
    allow_webcam = ask_user_permissions()
    track_loop(webcam_enabled=allow_webcam)
