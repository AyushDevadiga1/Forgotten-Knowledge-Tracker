# tracker_app/main.py — FKT 2.0 Phase 8
# Adds background warm-up thread so models are ready before first cycle.

import logging
import threading
from tracker_app.tracking.loop import track_loop, ask_user_permissions, warm_up_all_pipelines
from tracker_app.config import setup_directories

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    setup_directories()
    print("Forgotten Knowledge Tracker 2.0 initialising...")

    allow_webcam = ask_user_permissions()

    # Start warming up models while user reads the permission screen output
    warm_thread = threading.Thread(
        target=warm_up_all_pipelines,
        args=(allow_webcam,),
        daemon=True,
        name="fkt-warmup",
    )
    warm_thread.start()

    track_loop(webcam_enabled=allow_webcam)
