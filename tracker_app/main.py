"""FKT entry point — starts the tracking loop with background model warm-up."""

import logging
import os
import threading
from tracker_app.tracking.loop import track_loop, warm_up_all_pipelines
from tracker_app.config import setup_directories


def ask_user_permissions() -> bool:
    """Explain webcam vs CLE options and prompt the user. CLI concern only."""
    # Non-interactive override (matches README: "set ALLOW_WEBCAM in .env").
    # Use from config so the constant is the single source of truth.
    from tracker_app.config import USER_ALLOW_WEBCAM

    if "ALLOW_WEBCAM" in os.environ:
        if USER_ALLOW_WEBCAM:
            print("  [OK] ALLOW_WEBCAM=true — webcam enabled.\n")
        else:
            print("  [OK] ALLOW_WEBCAM=false — webcam disabled (CLE keystroke-based).\n")
        return USER_ALLOW_WEBCAM
    print()
    print("=" * 55)
    print("  FKT 2.0 — Attention Tracking")
    print("=" * 55)
    print()
    print("  FKT tracks your focus level to weight how strongly")
    print("  each concept is remembered in your knowledge graph.")
    print()
    print("  OPTION 1 — Webcam (Recommended)")
    print("    Eye-tracking via MediaPipe FaceMesh.")
    print("    Highest accuracy. 100% local — no cloud.")
    print()
    print("  OPTION 2 — Keystroke-only (CLE Fallback)")
    print("    Typing rhythm analysis. No camera needed.")
    print("    Still effective — especially during active typing.")
    print()
    print("  Change anytime: set ALLOW_WEBCAM in .env")
    print()
    while True:
        val = input("  Enable webcam? (y/n): ").strip().lower()
        if val in ("y", "yes"):
            print("\n  [OK] Webcam enabled. CLE also active as backup.\n")
            return True
        if val in ("n", "no"):
            print("\n  [OK] Webcam disabled. Using CLE (keystroke-based).")
            print("       Tip: enable webcam later for better accuracy.\n")
            return False
        print("  Please enter 'y' or 'n'.")


if __name__ == "__main__":
    from tracker_app.config import LOGS_DIR

    log_file = LOGS_DIR / "tracker.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
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
