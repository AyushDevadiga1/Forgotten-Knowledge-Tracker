"""Main tracking loop: orchestrates OCR, audio, webcam, and intent pipelines."""

import time
import logging
import threading
from threading import Event
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, Tuple

import psutil
from pynput import keyboard, mouse

from tracker_app.config import (
    TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL,
    SESSION_ALLOWED_INTENTS,
)
from tracker_app.db.db_module import init_all_databases
from tracker_app.tracking.activity_monitor import ActivityMonitor
from tracker_app.tracking.intent_module import predict_intent
from tracker_app.tracking.cle_module import get_cle
from tracker_app.tracking.session_state import is_active as session_is_active
from tracker_app.tracking.privacy_filter import is_sensitive_window

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


# ─── Input listener factory ───────────────────────────────────────────────────
# Callbacks are closures over the loop-local monitor/cle so that importing
# this module does NOT instantiate any live resources at module load time.

def _make_listeners(monitor, cle):
    """Return (on_key_press, on_mouse_click) closures bound to monitor/cle."""
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

    return on_key_press, on_mouse_click


def start_listeners(monitor, cle):
    """Start keyboard and mouse listeners bound to the provided monitor/cle."""
    on_key_press, on_mouse_click = _make_listeners(monitor, cle)
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

def get_active_window(monitor) -> Tuple[str, float]:
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
    cle,
) -> float:
    """Blend webcam EAR (70%) and CLE (30%). CLE-only when webcam disabled."""
    cle_score = cle.get_cle_score()['cle_score'] * 100
    if webcam_enabled and webcam_result is not None:
        webcam_score = webcam_result.get('attentiveness_score', 50.0)
        return round(0.70 * webcam_score + 0.30 * cle_score, 1)
    return round(cle_score, 1)


# ─── Adaptive interval throttling ─────────────────────────────────────────────

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


# ─── Pipeline warm-up ─────────────────────────────────────────────────────────

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
        import tracker_app.tracking.audio_module  # heuristics-only since ADR-002; import warms sounddevice
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

    try:
        # Pre-build the knowledge graph here (background thread at startup) so
        # the micro-quiz hot path never triggers a multi-minute embed+sync while
        # the tracking loop is mid-session.
        from tracker_app.tracking.knowledge_graph import get_graph
        get_graph()
        log.info("  knowledge graph ready")
    except Exception as e:
        log.warning(f"  knowledge graph: {e}")

    log.info("Warm-up complete.")


# ─── Safe pipeline runner ─────────────────────────────────────────────────────

def _safe_run(fn):
    """Wrap a pipeline call to catch all exceptions gracefully."""
    try:
        return fn()
    except Exception as e:
        logger.warning(f"Pipeline error ({fn}): {e}")
        return None


# ─── Idle tracking for quiz trigger ───────────────────────────────────────────

_idle_cycles = 0


def _maybe_trigger_quiz(
    intent_label: str,
    webcam_enabled: bool,
    attention_score: float,
):
    """Check idle state and broadcast a micro-quiz if conditions are met."""
    global _idle_cycles
    # Never interrupt outside a study session — nobody is present to answer.
    if not session_is_active():
        _idle_cycles = 0
        return
    if intent_label == 'idle':
        _idle_cycles += 1
    else:
        _idle_cycles = 0

    try:
        from tracker_app.tracking.quiz_engine import (
            should_show_quiz, generate_micro_quiz
        )
        from tracker_app.tracking.knowledge_graph import get_graph
        if should_show_quiz(
            _idle_cycles, webcam_enabled, attention_score,
            session_active=session_is_active(),
        ):
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

    # H-1: a previous track_loop() run in the same process (test runs,
    # signal-based reload) leaves stale state behind -- accumulated idle
    # cycles could fire a quiz on the very first cycle of a fresh run, and
    # a leftover cooldown timer could censor the first quiz of the session.
    global _idle_cycles
    _idle_cycles = 0
    from tracker_app.tracking.quiz_engine import reset_quiz_state
    reset_quiz_state()

    # ── Create session-scoped singletons here, not at module import ───────────
    monitor = ActivityMonitor()
    cle     = get_cle()

    kb_listener, ms_listener = start_listeners(monitor, cle)
    if not kb_listener or not ms_listener:
        logger.error("Failed to start input listeners — aborting.")
        return

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

            # ── Study-session gate ────────────────────────────────────────────
            # Concept capture only runs while the user has toggled a study
            # session on (via the dashboard). While inactive the loop idles
            # (no OCR/audio/webcam capture) but keeps watching for the toggle.
            if not session_is_active():
                if monitor.is_running:
                    monitor.end_session()
                time.sleep(max(0.05, TRACK_INTERVAL - (time.time() - cycle_start)))
                continue

            if not monitor.is_running:
                monitor.start_session()
                # Drop any input counts accumulated while idle so the first
                # cycle's interaction_rate reflects fresh activity, and restart
                # the capture cadence for a clean per-session rhythm.
                monitor.keyboard_counter.get_and_reset()
                monitor.mouse_counter.get_and_reset()
                audio_counter = ocr_counter = webcam_counter = save_counter = 0

            window_title, interaction_rate = get_active_window(monitor)

            # Privacy: a sensitive window title (bank, login, medical…) is
            # never persisted — the OCR capture was already skipped for it, so
            # storing the title would leak exactly the info we refused to read.
            context = "" if is_sensitive_window(window_title) else window_title

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

            # Collect results (with timeout to prevent stalling the loop).
            # Concepts are NOT persisted here — intent gating happens below.
            for name, future in futures.items():
                try:
                    result = future.result(timeout=8)
                    if result is None:
                        continue
                    if name == 'ocr':
                        ocr_result = result
                    elif name == 'webcam':
                        webcam_result = result
                except Exception as e:
                    logger.warning(f"{name} pipeline future error: {e}")

            # ── Unified attention score ───────────────────────────────────────
            attention_score = _get_attention_score(webcam_enabled, webcam_result, cle)
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
                monitor.process_intent(intent_result, context=context)
            except Exception as e:
                logger.warning(f"Intent prediction error: {e}")

            # ── Intent-gated concept capture ──────────────────────────────────
            # Even inside a study session, only persist concepts on cycles the
            # intent classifier labels as active studying, so a mid-session
            # distraction (YouTube tab, chat message) is not captured.
            intent_label = intent_result.get('intent_label', 'unknown')
            if intent_label in SESSION_ALLOWED_INTENTS:
                monitor.process_concepts(
                    ocr_result.get('keywords', {}),
                    attention_score=attention_score,  # AWFC
                )

            # ── Micro-quiz interrupt ──────────────────────────────────────────
            _maybe_trigger_quiz(
                intent_label,
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


# ask_user_permissions has been moved to tracker_app/main.py
# (CLI concerns do not belong in the tracking engine)
