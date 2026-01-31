# ==========================================================
# core/tracker.py | IEEE v4.0 Async Multi-Modal Upgrade
# ==========================================================
"""
Async FKT Tracker (IEEE-Ready, Multi-Modal)
--------------------------------------------
- Captures audio, OCR, webcam concurrently
- Predicts intent
- Updates knowledge graph & memory model
- Logs multi-modal events to DB
- Sends reminders dynamically
- Fully async & non-blocking
- Robust error handling and logging
"""

import os
import pickle
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from pynput import keyboard, mouse
import win32gui
from plyer import notification

from config import DB_PATH, TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL, USER_ALLOW_WEBCAM
from core.db_module import init_all_tables, init_multi_modal_table, init_memory_decay_table, log_multi_modal_event
from core.ocr_module import ocr_pipeline
from core.audio_module import record_audio, extract_features as audio_extract_features
from core.webcam_module import webcam_pipeline
from core.intent_module import extract_features as intent_extract_features
from core.knowledge_graph import add_concepts, get_graph, add_multimodal_edges, save_graph
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve

# ----------------------------- Logger Setup -----------------------------
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/tracker_async.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ----------------------------- Load classifiers -----------------------------
audio_clf, intent_clf, intent_label_map = None, None, None
try:
    if os.path.exists("core/audio_classifier.pkl"):
        with open("core/audio_classifier.pkl", "rb") as f:
            audio_clf = pickle.load(f)
        logger.info("Audio classifier loaded.")
except Exception:
    logger.exception("Failed to load audio classifier.")

try:
    if os.path.exists("core/intent_classifier.pkl") and os.path.exists("core/intent_label_map.pkl"):
        with open("core/intent_classifier.pkl", "rb") as f:
            intent_clf = pickle.load(f)
        with open("core/intent_label_map.pkl", "rb") as f:
            intent_label_map = pickle.load(f)
        logger.info("Intent classifier & label map loaded.")
except Exception:
    logger.exception("Failed to load intent classifier or label map.")

# ----------------------------- User Consent -----------------------------
def ask_user_permissions() -> None:
    global USER_ALLOW_WEBCAM
    try:
        choice = input("Enable webcam attention tracking? (y/n): ").strip().lower()
        USER_ALLOW_WEBCAM = choice == "y"
        logger.info("User webcam consent: %s", USER_ALLOW_WEBCAM)
    except Exception:
        USER_ALLOW_WEBCAM = False
        logger.warning("Defaulting webcam consent to False.")

# ----------------------------- Interaction Counter -----------------------------
class InteractionCounter:
    def __init__(self):
        self.keyboard = 0
        self.mouse = 0

    def total(self) -> int:
        return self.keyboard + self.mouse

    def reset(self) -> None:
        self.keyboard = 0
        self.mouse = 0

counters = InteractionCounter()

def _on_key_press(_key) -> None:
    counters.keyboard += 1

def _on_mouse_click(_x, _y, _button, pressed) -> None:
    if pressed:
        counters.mouse += 1

def start_listeners() -> Tuple[keyboard.Listener, mouse.Listener]:
    kb = keyboard.Listener(on_press=_on_key_press)
    ms = mouse.Listener(on_click=_on_mouse_click)
    kb.start()
    ms.start()
    return kb, ms

# ----------------------------- Active Window -----------------------------
def get_active_window() -> Tuple[str, int]:
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or "Unknown"
    except Exception:
        title = "Unknown"
    return title, counters.total()

# ----------------------------- Globals -----------------------------
_latest_ocr: Dict[str, Any] = {}
_latest_attention: Optional[int] = 0
_latest_audio: str = "silence"
_latest_audio_conf: float = 0.0
_latest_intent: Dict[str, Any] = {"intent_label": "unknown", "confidence": 0.0}
MEMORY_THRESHOLD = 0.6
REMINDER_COOLDOWN = timedelta(minutes=30)

# ----------------------------- Memory & Reminders -----------------------------
def maybe_notify(concept: str, memory_score: float, graph, use_attention: bool = True) -> None:
    now = datetime.now()
    last_reminded_str = graph.nodes[concept].get("last_reminded_time")
    try:
        last_reminded = datetime.fromisoformat(last_reminded_str) if last_reminded_str else now - REMINDER_COOLDOWN
    except Exception:
        last_reminded = now - REMINDER_COOLDOWN

    if memory_score < MEMORY_THRESHOLD and (now - last_reminded >= REMINDER_COOLDOWN):
        try:
            notification.notify(
                title="Time to Review!",
                message=f"Concept: {concept}\nMemory Score: {memory_score:.2f}",
                timeout=5,
            )
            graph.nodes[concept]["last_reminded_time"] = now.isoformat()
            graph.nodes[concept]["next_review_time"] = (now + timedelta(hours=1)).isoformat()
            logger.info("Reminder sent for concept '%s' (score: %.3f)", concept, memory_score)
        except Exception:
            logger.exception("Failed to send notification for concept '%s'", concept)

# ----------------------------- Async Loops -----------------------------
async def audio_loop(interval_sec: float):
    global _latest_audio, _latest_audio_conf
    while True:
        try:
            audio = record_audio()
            if audio_clf:
                feats = audio_extract_features(audio).reshape(1, -1)
                label = audio_clf.predict(feats)[0]
                confidence = float(max(audio_clf.predict_proba(feats)[0]))
                _latest_audio, _latest_audio_conf = label, confidence
        except Exception:
            _latest_audio, _latest_audio_conf = "unknown", 0.0
            logger.exception("Audio loop failed")
        await asyncio.sleep(interval_sec)

async def ocr_loop(interval_sec: float):
    global _latest_ocr
    while True:
        try:
            ocr_data = ocr_pipeline() or {}
            raw_keywords = ocr_data.get("keywords", {}) or {}
            normalized = {}
            for kw, info in raw_keywords.items():
                if isinstance(info, dict):
                    normalized[str(kw)] = {"score": float(info.get("score", 0.5)), "count": int(info.get("count", 1))}
                else:
                    normalized[str(kw)] = {"score": float(info), "count": 1}
            _latest_ocr = normalized
            if _latest_ocr:
                add_concepts(list(_latest_ocr.keys()))
        except Exception:
            _latest_ocr = {}
            logger.exception("OCR loop failed")
        await asyncio.sleep(interval_sec)

async def webcam_loop(interval_sec: float):
    global _latest_attention
    while True:
        try:
            if USER_ALLOW_WEBCAM:
                output = await webcam_pipeline()
                _latest_attention = int(output.get("attentive") or 0)
            else:
                _latest_attention = None
        except Exception:
            _latest_attention = None
            logger.exception("Webcam loop failed")
        await asyncio.sleep(interval_sec)

# ----------------------------- Intent Prediction -----------------------------
def predict_intent_live(
    ocr_keywords: Dict[str, Any],
    audio_label: str,
    attention_score: Optional[int],
    interaction_rate: int,
    use_webcam: bool = False,
) -> Dict[str, Any]:
    try:
        att = int(attention_score or 0)
        ir = int(interaction_rate or 0)
        features = intent_extract_features(ocr_keywords, audio_label, att, ir, use_webcam=use_webcam)
        if intent_clf and intent_label_map:
            pred_idx = intent_clf.predict(features)[0]
            confidence = float(max(intent_clf.predict_proba(features)[0]))
            try:
                label = intent_label_map.inverse_transform([int(pred_idx)])[0]
            except Exception:
                try:
                    label = intent_label_map[int(pred_idx)]
                except Exception:
                    label = str(pred_idx)
            return {"intent_label": label, "confidence": confidence}
        # fallback heuristics
        if audio_label == "speech" and ir > 5:
            if use_webcam and att > 50:
                return {"intent_label": "studying", "confidence": 0.8}
            return {"intent_label": "passive", "confidence": 0.6}
        if ir < 2:
            return {"intent_label": "idle", "confidence": 0.7}
        return {"intent_label": "passive", "confidence": 0.6}
    except Exception:
        logger.exception("Intent prediction failed")
        return {"intent_label": "unknown", "confidence": 0.0}

# ----------------------------- Tracker Main Loop -----------------------------
async def main_loop():
    init_db()
    init_multi_modal_db()
    init_memory_decay_db()
    kb_listener, ms_listener = start_listeners()
    G = get_graph()

    SAVE_INTERVAL = 300
    save_counter = 0

    try:
        while True:
            try:
                # Active window
                window, interaction_rate = get_active_window()

                # Memory & knowledge graph
                mem_scores = {}
                for concept, info in _latest_ocr.items():
                    if concept not in G.nodes:
                        add_concepts([concept])
                        G = get_graph()

                    last_review_str = G.nodes[concept].get("last_review")
                    try:
                        last_review = datetime.fromisoformat(last_review_str) if last_review_str else datetime.now()
                    except Exception:
                        last_review = datetime.now()

                    lambda_val = 0.1
                    intent_conf = float(G.nodes[concept].get("intent_conf", 1.0))
                    audio_conf = float(_latest_audio_conf)
                    kw_score = float(info.get("score", 0.5))
                    count = int(info.get("count", 1))
                    att_score = int(_latest_attention) if _latest_attention is not None else None

                    mem_score = compute_memory_score(last_review, lambda_val, intent_conf, att_score, audio_conf)
                    mem_score *= min(1.0, kw_score + 0.5)
                    mem_score *= min(1.5, 1 + 0.05 * (count - 1))

                    next_review = schedule_next_review(last_review, mem_score, lambda_val)
                    G.nodes[concept]["memory_score"] = float(mem_score)
                    G.nodes[concept]["next_review_time"] = next_review.isoformat()
                    G.nodes[concept]["last_review"] = datetime.now().isoformat()
                    G.nodes[concept]["intent_conf"] = float(intent_conf)

                    maybe_notify(concept, mem_score, G, use_attention=(att_score is not None))
                    log_forgetting_curve(concept, last_review, observed_usage=count)
                    mem_scores[concept] = mem_score

                # Intent
                _latest_intent = predict_intent_live(_latest_ocr, _latest_audio, _latest_attention, interaction_rate, USER_ALLOW_WEBCAM)

                # Knowledge graph edges
                try:
                    add_multimodal_edges(_latest_ocr, _latest_audio, _latest_intent.get("intent_label", "unknown"))
                except Exception:
                    pass

                # Multi-modal logging
                memory_score = max(mem_scores.values() or [0.0])
                log_multi_modal_event(
                    window_title=window,
                    ocr_keywords=",".join(_latest_ocr.keys()),
                    audio_label=_latest_audio,
                    attention_score=_latest_attention or 0,
                    interaction_rate=interaction_rate,
                    intent_label=_latest_intent.get("intent_label", "unknown"),
                    intent_confidence=float(_latest_intent.get("confidence", 0.0)),
                    memory_score=memory_score,
                    source_module="TrackerAsync"
                )

                # Console summary
                print(f"\n[Session Summary]")
                print(f"Window: {window}")
                print(f"Intent: {_latest_intent.get('intent_label')} | Confidence: {_latest_intent.get('confidence', 0.0):.2f}")
                print(f"Audio: {_latest_audio}")
                print(f"Attention: {_latest_attention}")
                print(f"OCR Keywords: {list(_latest_ocr.keys())[:5]}{'...' if len(_latest_ocr) > 5 else ''}")
                print(f"Memory Score (max concept): {memory_score:.3f}")
                print("-" * 40)

                await asyncio.sleep(TRACK_INTERVAL)
                save_counter += TRACK_INTERVAL
                if save_counter >= SAVE_INTERVAL:
                    save_graph()
                    save_counter = 0

            except Exception:
                await asyncio.sleep(TRACK_INTERVAL)
                continue
    finally:
        try:
            save_graph()
        except Exception:
            pass
        try:
            kb_listener.stop()
            ms_listener.stop()
        except Exception:
            pass
        logger.info("Async tracker terminated cleanly.")

# ----------------------------- Entry Point -----------------------------
if __name__ == "__main__":
    ask_user_permissions()
    loop = asyncio.get_event_loop()
    tasks = [
        audio_loop(AUDIO_INTERVAL),
        ocr_loop(SCREENSHOT_INTERVAL),
        webcam_loop(WEBCAM_INTERVAL),
        main_loop()
    ]
    loop.run_until_complete(asyncio.gather(*tasks))
