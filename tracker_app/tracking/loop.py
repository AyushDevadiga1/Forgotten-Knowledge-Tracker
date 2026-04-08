# tracking/loop.py — FKT 2.0 Phase 8 (Performance Hardening)
# Changes in this version:
#   Phase 5: async audio pipeline (non-blocking)
#   Phase 7: micro-quiz interrupt wired in
#   Phase 8: ThreadPoolExecutor for parallel pipelines
#            SSIM-based screenshot deduplication
#            Adaptive CPU throttling (psutil)
#            Pipeline warm-up on startup
#            Fixed: attention_score used-before-assignment bug

import time
import logging
import threading
from threading import Event
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, Tuple

import psutil
from pynput import keyboard, mouse

from tracker_app.config import (
    TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL
)
from tracker_app.db.db_module import init_all_databases
from tracker_app.tracking.activity_monitor import ActivityMonitor
from tracker_app.tracking.intent_module import predict_intent
from tracker_app.tracking.cle_module import get_cle

logger = logging.getLogger("TrackerLoop")

# ─── Lazy pipeline loaders ────────────────────────────────────────────────────

_ocr_pipeline    = None
_audio_pipeline  = None
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
        from tracker_app.tracking.audio_module import (
            audio_pipeline_async, get_cached_audio_result
        )
        _audio_pipeline = (audio_pipeline_async, get_cached_audio_result)
    return _audio_pipeline


def get_webcam_pipeline():
    global _webcam_pipeline
    if _webcam_pipeline is None:
        from tracker_app.tracking.webcam_module import webcam_pipeline
        _webcam_pipeline = webcam_pipeline
    return _webcam_pipeline


# ─── Activity monitor + CLE singletons ───────────────────────────────────────

monitor = ActivityMonitor()
cle     = get_cle()


# ─── Input listeners ─────────────────────────────────────────────────────────

def on_key_press(key):
    monitor.keyboard_counter.increment()
    try:
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
        kb = keyboard.Listener(on_press=on_key_press)
        ms = mouse.Listener(on_click=on_mouse_click)
        kb.start()
        ms.start()
        logger.info("Input listeners started (keyboard + mouse + CLE).")
        return kb, ms
    except Exception as e:
        logger.error(f"Failed to start input listeners: {e}")
        return None, None


# ─── Window / interaction ─────────────────────────────────────────────────────

def get_active_window() -> Tuple[str, float]:
    """Return (window_title, interaction_rate_per_second)."""
    try:
        try:
            import win32gui
            hwnd  = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd) or "Unknown"
        except ImportError:
            title = "Unknown"
        kb_events = monitor.keyboard_counter.get_and_reset()
        ms_events = monitor.mouse_counter.get_and_reset()
        total     = kb_events + ms_events
        rate      = min(total / TRACK_INTERVAL if TRACK_INTERVAL > 0 else 0, 100)
        return title, rate
    except Exception as e:
        logger.error(f"get_active_window error: {e}")
        return "Unknown", 0


# ─── Attention blending ───────────────────────────────────────────────────────

def _get_attention_score(
    webcam_enabled: bool,
    webcam_result: Optional[dict],
) -> float:
    """Blend webcam EAR (70%) and CLE (30%). CLE-only when webcam disabled."""
    cle_score = cle.get_cle_score()['cle_score'] * 100
    if webcam_enabled and webcam_result is not None:
        webcam_score = webcam_result.get('attentiveness_score', 50.0)
        return round(0.70 * webcam_score + 0.30 * cle_score, 1)
    return round(cle_score, 1)


# ─── Phase 8: adaptive interval throttling ────────────────────────────────────

def _get_effective_intervals() -> dict:
    """
    Scale OCR and audio intervals based on current CPU load.
    High CPU → back off sampling to avoid competing with user's work.
    """
    cpu = psutil.cpu_percent(interval=0.2)
    if cpu > 70:
        mult = 2.5
    elif cpu > 50:
        mult = 1.5
    else:
        mult = 1.0
    return {
        'ocr':    SCREENSHOT_INTERVAL * mult,
        'audio':  AUDIO_INTERVAL      * mult,
        'webcam': WEBCAM_INTERVAL,           # already infrequent — don't throttle
    }


# ─── Phase 8: pipeline warm-up ───────────────────────────────────────────────

def warm_up_all_pipelines(webcam_enabled: bool = True):
    """
    Pre-load lazy models in a background thread during startup.
    Moves cold-start latency away from the first tracking cycle.
    """
    log = logging.getLogger("WarmUp")
    log.info("Pre-loading models...")

    try:
        from tracker_app.tracking.keyword_extractor import get_keyword_extractor
        get_keyword_extractor()
        log.info("  keyword extractor ready")
    except Exception as e:
        log.warning(f"  keyword extractor: {e}")

    try:
        from tracker_app.tracking.intent_module import _load_model
        _load_model()
        log.info("  intent classifier ready")
    except Exception as e:
        log.warning(f"  intent classifier: {e}")

    try:
        from tracker_app.tracking.audio_module import _load_classifier
        _load_classifier()
        log.info("  audio classifier ready")
    except Exception as e:
        log.warning(f"  audio classifier: {e}")

    if webcam_enabled:
        try:
            from tracker_app.tracking.webcam_module import _get_face_mesh
            _get_face_mesh()
            log.info("  mediapipe face mesh ready")
        except Exception as e:
            log.warning(f"  face mesh: {e}")

    log.info("Warm-up complete.")


# ─── Phase 8: safe pipeline runner ───────────────────────────────────────────

def _safe_run(fn):
    """Wrap a pipeline call to catch all exceptions gracefully."""
    try:
        return fn()
    except Exception as e:
        logger.warning(f"Pipeline error ({fn}): {e}")
        return None


# ─── Idle tracking for Phase 7 quiz trigger ──────────────────────────────────

_idle_cycles = 0


def _maybe_trigger_quiz(
    intent_label: str,
    webcam_enabled: bool,
    attention_score: float,
):
    """Check idle state and broadcast a micro-quiz if conditions are met."""
    global _idle_cycles
    if intent_label == 'idle':
        _idle_cycles += 1
    else:
        _idle_cycles = 0

    try:
        from tracker_app.tracking.quiz_engine import (
            should_show_quiz, generate_micro_quiz
        )
        from tracker_app.tracking.knowledge_graph import get_graph
        if should_show_quiz(_idle_cycles, webcam_enabled, attention_score):
            graph = get_graph()
            quiz  = generate_micro_quiz(graph)
            if quiz:
                try:
                    from tracker_app.web.realtime import broadcast_micro_quiz
                    broadcast_micro_quiz(quiz)
                except Exception:
                    pass  # dashboard may not be running
                logger.info(f"Micro-quiz triggered: '{quiz['concept']}'")
    except Exception as e:
        logger.debug(f"Quiz engine skipped: {e}")


# ─── Main tracking loop ───────────────────────────────────────────────────────

def track_loop(
    stop_event: Optional[Event] = None,
    webcam_enabled: bool = True,
):
    if stop_event is None:
        stop_event = Event()

    logger.info("FKT 2.0 tracking loop starting...")
    logger.info(
        f"Webcam: {'ENABLED' if webcam_enabled else 'DISABLED (CLE fallback)'}"
    )

    init_all_databases()

    kb_listener, ms_listener = start_listeners()
    if not kb_listener or not ms_listener:
        logger.error("Failed to start input listeners — aborting.")
        return

    monitor.start_session()
    cle.reset()

    audio_counter = ocr_counter = webcam_counter = save_counter = 0
    ocr_result    = {'keywords': {}}
    audio_result  = {'audio_label': 'silence', 'confidence': 0.9}
    webcam_result: Optional[dict] = None

    # Compute attention BEFORE first cycle so the variable always exists
    attention_score: float = 50.0

    # ── Thread pool for parallel pipelines ───────────────────────────────────
    executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="fkt-pipeline")

    try:
        while not stop_event.is_set():
            cycle_start = time.time()
            window_title, interaction_rate = get_active_window()

            # Adaptive intervals based on current CPU
            intervals = _get_effective_intervals()

            # ── Kick off async audio (non-blocking) ──────────────────────────
            audio_counter += TRACK_INTERVAL
            if audio_counter >= intervals['audio']:
                try:
                    audio_async, _ = get_audio_pipeline()
                    audio_async()   # background thread — returns immediately
                except Exception as e:
                    logger.warning(f"Audio launch error: {e}")
                audio_counter = 0

            # Always read the latest cached audio result
            try:
                _, get_cached = get_audio_pipeline()
                audio_result = get_cached()
            except Exception:
                pass

            # ── OCR + Webcam in parallel via thread pool ──────────────────────
            ocr_counter    += TRACK_INTERVAL
            webcam_counter += TRACK_INTERVAL

            futures: dict[str, Future] = {}

            if ocr_counter >= intervals['ocr']:
                futures['ocr'] = executor.submit(_safe_run, get_ocr_pipeline())
                ocr_counter = 0

            if webcam_counter >= intervals['webcam'] and webcam_enabled:
                futures['webcam'] = executor.submit(_safe_run, get_webcam_pipeline())
                webcam_counter = 0

            # Collect results (with timeout to prevent stalling the loop)
            for name, future in futures.items():
                try:
                    result = future.result(timeout=8)
                    if result is None:
                        continue
                    if name == 'ocr':
                        ocr_result = result
                        monitor.process_concepts(
                            ocr_result.get('keywords', {}),
                            attention_score=attention_score,  # AWFC
                        )
                    elif name == 'webcam':
                        webcam_result = result
                except Exception as e:
                    logger.warning(f"{name} pipeline future error: {e}")

            # ── Unified attention score ───────────────────────────────────────
            attention_score = _get_attention_score(webcam_enabled, webcam_result)
            monitor.update_attention(attention_score)

            # ── Intent prediction ─────────────────────────────────────────────
            intent_result = {'intent_label': 'unknown', 'confidence': 0.0}
            try:
                intent_result = predict_intent(
                    ocr_keywords=ocr_result.get('keywords', {}),
                    audio_label=audio_result.get('audio_label', 'silence'),
                    attention_score=attention_score,
                    interaction_rate=interaction_rate,
                    use_webcam=webcam_enabled,
                    audio_confidence=audio_result.get('confidence', 0.7),
                )
                monitor.process_intent(intent_result, context=window_title)
            except Exception as e:
                logger.warning(f"Intent prediction error: {e}")

            # ── Phase 7: Micro-quiz interrupt ─────────────────────────────────
            _maybe_trigger_quiz(
                intent_result.get('intent_label', 'unknown'),
                webcam_enabled,
                attention_score,
            )

            # ── Periodic export (every 5 min) ─────────────────────────────────
            save_counter += TRACK_INTERVAL
            if save_counter >= 300:
                try:
                    monitor.export_tracking_data()
                except Exception as e:
                    logger.warning(f"Export error: {e}")
                save_counter = 0

            # ── Sleep for remainder of cycle ──────────────────────────────────
            elapsed = time.time() - cycle_start
            time.sleep(max(0.05, TRACK_INTERVAL - elapsed))

    except KeyboardInterrupt:
        logger.info("Tracking interrupted by user.")
    finally:
        executor.shutdown(wait=False)
        monitor.end_session()
        if kb_listener:
            kb_listener.stop()
        if ms_listener:
            ms_listener.stop()
        logger.info("FKT tracking loop shut down cleanly.")


# ─── Permissions prompt ───────────────────────────────────────────────────────

def ask_user_permissions() -> bool:
    """Explain webcam vs CLE options. Strongly encourages webcam."""
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
        if val in ('y', 'yes'):
            print("\n  [OK] Webcam enabled. CLE also active as backup.\n")
            return True
        if val in ('n', 'no'):
            print("\n  [OK] Webcam disabled. Using CLE (keystroke-based).")
            print("       Tip: enable webcam later for better accuracy.\n")
            return False
        print("  Please enter 'y' or 'n'.")
