# tracking/loop.py — FKT 2.0
# Key changes from v1:
#   - CLE (Cognitive Load Estimator) wired into key/mouse listeners
#   - CLE score used as attention fallback when webcam is disabled
#   - Webcam is optional but strongly encouraged with clear explanation
#   - interaction_rate now comes from the event counters correctly
#   - Webcam result properly guards None before updating attention
import time
import logging
from threading import Event
from typing import Optional, Tuple
from pynput import keyboard, mouse

from tracker_app.config import TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL
from tracker_app.db.db_module import init_all_databases
from tracker_app.tracking.activity_monitor import ActivityMonitor
from tracker_app.tracking.intent_module import predict_intent
from tracker_app.tracking.cle_module import get_cle

logger = logging.getLogger("TrackerLoop")

# ----------------------------
# Lazy-loaded heavy pipelines
# ----------------------------
_ocr_pipeline = None
_audio_pipeline = None
_webcam_pipeline = None

def get_ocr_pipeline():
    global _ocr_pipeline
    if _ocr_pipeline is None:
        from tracker_app.tracking.ocr_module import ocr_pipeline
        _ocr_pipeline = ocr_pipeline
    return _ocr_pipeline

def get_audio_pipeline():
    global _audio_pipeline
    if _audio_pipeline is None:
        from tracker_app.tracking.audio_module import audio_pipeline
        _audio_pipeline = audio_pipeline
    return _audio_pipeline

def get_webcam_pipeline():
    global _webcam_pipeline
    if _webcam_pipeline is None:
        from tracker_app.tracking.webcam_module import webcam_pipeline
        _webcam_pipeline = webcam_pipeline
    return _webcam_pipeline

# ----------------------------
# Activity monitor (singleton)
# ----------------------------
monitor = ActivityMonitor()
cle = get_cle()  # Cognitive Load Estimator — shared global instance

# ----------------------------
# Input listeners
# Feed BOTH the ActivityMonitor counter AND the CLE simultaneously
# ----------------------------
def on_key_press(key):
    monitor.keyboard_counter.increment()
    try:
        # Detect backspace for CLE backspace-rate signal
        from pynput.keyboard import Key
        is_backspace = (key == Key.backspace)
    except Exception:
        is_backspace = False
    cle.record_key(is_backspace=is_backspace)

def on_mouse_click(x, y, button, pressed):
    if pressed:
        monitor.mouse_counter.increment()
        cle.record_mouse_click()

def start_listeners():
    try:
        kb_listener = keyboard.Listener(on_press=on_key_press)
        ms_listener = mouse.Listener(on_click=on_mouse_click)
        kb_listener.start()
        ms_listener.start()
        logger.info("Input listeners started (keyboard + mouse + CLE).")
        return kb_listener, ms_listener
    except Exception as e:
        logger.error(f"Error starting input listeners: {e}")
        return None, None

# ----------------------------
# Window / interaction helpers
# ----------------------------
def get_active_window() -> Tuple[str, float]:
    """Return (window_title, interaction_rate_per_second)."""
    try:
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd) or "Unknown"
        except ImportError:
            title = "Unknown"  # Non-Windows fallback
        # get_and_reset resets the counter so each cycle measures fresh events
        kb_events = monitor.keyboard_counter.get_and_reset()
        ms_events = monitor.mouse_counter.get_and_reset()
        total_events = kb_events + ms_events
        interaction_rate = min(
            total_events / TRACK_INTERVAL if TRACK_INTERVAL > 0 else 0, 100
        )
        return title, interaction_rate
    except Exception as e:
        logger.error(f"get_active_window error: {e}")
        return "Unknown", 0

def _get_attention_score(webcam_enabled: bool, webcam_result: Optional[dict]) -> float:
    """
    Return an attention score 0–100.
    Priority:
      1. Webcam EAR score  (if webcam enabled and face detected)
      2. CLE score × 100  (keystroke dynamics — always running)
    When both are available, blend them 70/30 in favour of webcam.
    """
    cle_result = cle.get_cle_score()
    cle_score = cle_result['cle_score'] * 100  # scale to 0–100

    if webcam_enabled and webcam_result is not None:
        webcam_score = webcam_result.get('attentiveness_score', 50.0)
        # Blend: webcam 70%, CLE 30%
        return round(0.70 * webcam_score + 0.30 * cle_score, 1)

    # Webcam disabled or unavailable — CLE is sole signal
    return round(cle_score, 1)

# ----------------------------
# Main tracking loop
# ----------------------------
def track_loop(stop_event: Optional[Event] = None, webcam_enabled: bool = True):
    if stop_event is None:
        stop_event = Event()

    logger.info("FKT 2.0 tracking loop starting...")
    logger.info(f"Webcam attention: {'ENABLED' if webcam_enabled else 'DISABLED (CLE fallback active)'}")

    init_all_databases()
    kb_listener, ms_listener = start_listeners()
    if not kb_listener or not ms_listener:
        logger.error("Failed to start input listeners — aborting.")
        return

    monitor.start_session()
    cle.reset()

    audio_counter = ocr_counter = webcam_counter = save_counter = 0
    ocr_result  = {'keywords': {}}
    audio_result = {'audio_label': 'silence'}
    webcam_result: Optional[dict] = None

    try:
        while not stop_event.is_set():
            cycle_start = time.time()
            window_title, interaction_rate = get_active_window()

            # --- Audio pipeline ---
            audio_counter += TRACK_INTERVAL
            if audio_counter >= AUDIO_INTERVAL:
                try:
                    audio_result = get_audio_pipeline()()
                except Exception as e:
                    logger.warning(f"Audio error: {e}")
                audio_counter = 0

            # --- OCR pipeline ---
            ocr_counter += TRACK_INTERVAL
            if ocr_counter >= SCREENSHOT_INTERVAL:
                try:
                    ocr_result = get_ocr_pipeline()()
                    if ocr_result:
                        monitor.process_concepts(ocr_result.get('keywords', {}))
                except Exception as e:
                    logger.warning(f"OCR error: {e}")
                ocr_counter = 0

            # --- Webcam pipeline (optional) ---
            webcam_counter += TRACK_INTERVAL
            if webcam_counter >= WEBCAM_INTERVAL:
                if webcam_enabled:
                    try:
                        webcam_result = get_webcam_pipeline()()
                    except Exception as e:
                        logger.warning(f"Webcam error: {e}")
                        webcam_result = None
                webcam_counter = 0

            # --- Unified attention score (webcam + CLE blend) ---
            attention_score = _get_attention_score(webcam_enabled, webcam_result)
            monitor.update_attention(attention_score)

            # --- Intent prediction ---
            try:
                intent_result = predict_intent(
                    ocr_keywords=ocr_result.get('keywords', {}),
                    audio_label=audio_result.get('audio_label', 'silence'),
                    attention_score=attention_score,
                    interaction_rate=interaction_rate,
                    use_webcam=webcam_enabled
                )
                monitor.process_intent(intent_result, context=window_title)
            except Exception as e:
                logger.warning(f"Intent prediction error: {e}")

            # --- Periodic data export (every 5 min) ---
            save_counter += TRACK_INTERVAL
            if save_counter >= 300:
                try:
                    monitor.export_tracking_data()
                except Exception as e:
                    logger.warning(f"Export error: {e}")
                save_counter = 0

            elapsed = time.time() - cycle_start
            time.sleep(max(0.1, TRACK_INTERVAL - elapsed))

    except KeyboardInterrupt:
        logger.info("Tracking interrupted by user.")
    finally:
        monitor.end_session()
        if kb_listener:
            kb_listener.stop()
        if ms_listener:
            ms_listener.stop()
        logger.info("FKT tracking loop shut down cleanly.")


# ----------------------------
# Permissions prompt
# Strongly encourages webcam; explains CLE fallback
# ----------------------------
def ask_user_permissions() -> bool:
    """
    Ask the user whether to enable webcam attention tracking.
    Explains both options clearly so an informed decision is made.
    Webcam is optional but strongly recommended for best results.
    """
    print()
    print("="*55)
    print("  FKT 2.0 — Attention Tracking")
    print("="*55)
    print()
    print("  FKT tracks your attention level to weight how strongly")
    print("  each concept is stored in your knowledge graph.")
    print()
    print("  OPTION 1 — Webcam (Recommended)")
    print("    Uses eye-tracking via MediaPipe FaceMesh.")
    print("    More accurate attention scores.")
    print("    Runs 100% locally — no data leaves your machine.")
    print()
    print("  OPTION 2 — Keystroke-only (Fallback)")
    print("    Uses typing rhythm analysis (Cognitive Load Estimator).")
    print("    No camera required. Still effective.")
    print("    Recommended if you have no webcam or prefer not to use it.")
    print()
    print("  You can change this any time in config.py.")
    print()

    while True:
        val = input("  Enable webcam? (y/n): ").strip().lower()
        if val in ('y', 'yes'):
            print()
            print("  [OK] Webcam enabled. Keystroke CLE also running as backup.")
            print()
            return True
        elif val in ('n', 'no'):
            print()
            print("  [OK] Webcam disabled. Using Cognitive Load Estimator (keystroke-based).")
            print("       Tip: You can enable webcam later in config.py for better accuracy.")
            print()
            return False
        else:
            print("  Please enter 'y' or 'n'.")
