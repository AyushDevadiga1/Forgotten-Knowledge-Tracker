# ==========================================================
# core/tracker.py | Upgraded Tracker with OCR v2, Memory, Intent, Reminders
# ==========================================================

import time
import sqlite3
import json
import pickle
import os
from threading import Event
from datetime import datetime, timedelta

from pynput import keyboard, mouse
import win32gui
from plyer import notification

from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db
from config import DB_PATH, TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL, USER_ALLOW_WEBCAM
from core.ocr_module import ocr_pipeline
from core.audio_module import record_audio, extract_features as audio_extract_features
from core.webcam_module import webcam_pipeline
from core.intent_module import extract_features as intent_extract_features, predict_intent
from core.knowledge_graph import add_concepts, get_graph, add_edges
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve
from core.face_detection_module import FaceDetector

# -----------------------------
# Load classifiers
# -----------------------------
audio_clf_path = "core/audio_classifier.pkl"
if os.path.exists(audio_clf_path):
    with open(audio_clf_path, "rb") as f:
        audio_clf = pickle.load(f)
    print("Audio classifier loaded.")
else:
    audio_clf = None
    print("Audio classifier not found. Will use default labels.")

intent_clf_path = "core/intent_classifier.pkl"
intent_map_path = "core/intent_label_map.pkl"
if os.path.exists(intent_clf_path) and os.path.exists(intent_map_path):
    with open(intent_clf_path, "rb") as f:
        intent_clf = pickle.load(f)
    with open(intent_map_path, "rb") as f:
        intent_label_map = pickle.load(f)
    print("Intent classifier loaded.")
else:
    intent_clf = None
    intent_label_map = None
    print("Intent classifier not found. Will use fallback rules.")

# -----------------------------
# User consent
# -----------------------------
def ask_user_permissions():
    global USER_ALLOW_WEBCAM
    choice = input("Do you want to enable webcam attention tracking? (y/n): ").lower()
    USER_ALLOW_WEBCAM = choice == "y"

# -----------------------------
# Global counters
# -----------------------------
keyboard_events = 0
mouse_events = 0

# -----------------------------
# Interaction listeners
# -----------------------------
def on_key_press(key):
    global keyboard_events
    keyboard_events += 1

def on_mouse_click(x, y, button, pressed):
    global mouse_events
    if pressed:
        mouse_events += 1

def start_listeners():
    kb_listener = keyboard.Listener(on_press=on_key_press)
    ms_listener = mouse.Listener(on_click=on_mouse_click)
    kb_listener.start()
    ms_listener.start()
    return kb_listener, ms_listener

# -----------------------------
# Active window + interaction
# -----------------------------
def get_active_window():
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd) or "Unknown"
    interaction_rate = int((keyboard_events or 0) + (mouse_events or 0))
    return title, interaction_rate

# -----------------------------
# Log session to DB
# -----------------------------
def log_session(window_title, interaction_rate):
    global keyboard_events, mouse_events
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app_name = window_title.split(" - ")[-1] if " - " in window_title else window_title
    interaction_rate = int(interaction_rate)

    try:
        c.execute("""INSERT INTO sessions 
                     (start_ts, end_ts, app_name, window_title, interaction_rate) 
                     VALUES (?, ?, ?, ?, ?)""",
                  (ts, ts, app_name, window_title, interaction_rate))
        conn.commit()
        print(f"Logged: {app_name}, Interaction: {interaction_rate}")
    except Exception as e:
        print(f"Failed to log session: {e}")
    finally:
        conn.close()

    keyboard_events = 0
    mouse_events = 0

# -----------------------------
# Log multi-modal data
# -----------------------------
def log_multi_modal(window, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score=0.0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if ocr_keywords is None:
        ocr_keywords = {}

    ocr_data_to_store = {}
    for kw, info in ocr_keywords.items():
        if isinstance(info, dict):
            ocr_data_to_store[kw] = {
                "score": float(info.get("score", 0.5)),
                "count": int(info.get("count", 1))
            }
        else:
            ocr_data_to_store[kw] = {"score": float(info), "count": 1}

    try:
        c.execute('''
            INSERT INTO multi_modal_logs
            (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            window,
            json.dumps(ocr_data_to_store),
            audio_label,
            int(attention_score),
            int(interaction_rate),
            intent_label,
            float(intent_confidence),
            float(memory_score)
        ))
        conn.commit()
    except Exception as e:
        print(f"Failed to write multi_modal_logs: {e}")
    finally:
        conn.close()

# -----------------------------
# Persist knowledge graph
# -----------------------------
def save_knowledge_graph():
    G = get_graph()
    os.makedirs("data", exist_ok=True)
    with open("data/knowledge_graph.pkl", "wb") as f:
        pickle.dump(G, f)
    print("Knowledge graph saved.")

# -----------------------------
# Predict audio
# -----------------------------
def classify_audio_live():
    audio = record_audio()
    if audio_clf:
        features = audio_extract_features(audio).reshape(1, -1)
        label = audio_clf.predict(features)[0]
        confidence = float(max(audio_clf.predict_proba(features)[0]))
        return label, confidence
    else:
        return "unknown", 0.0

# -----------------------------
# Predict intent
# -----------------------------
def predict_intent_live(ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam=False):
    try:
        attention_score = int(attention_score or 0)
        interaction_rate = int(interaction_rate or 0)

        features = intent_extract_features(
            ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam=use_webcam
        )

        if intent_clf is not None and intent_label_map is not None:
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
        else:
            # fallback rules
            if audio_label == "speech" and interaction_rate > 5:
                if use_webcam and attention_score > 50:
                    return {"intent_label": "studying", "confidence": 0.8}
                else:
                    return {"intent_label": "passive", "confidence": 0.6}
            elif interaction_rate < 2:
                return {"intent_label": "idle", "confidence": 0.7}
            else:
                return {"intent_label": "passive", "confidence": 0.6}

    except Exception as e:
        print(f"Intent prediction failed: {e}")
        return {"intent_label": "unknown", "confidence": 0.0}

# -----------------------------
# Memory & Reminder Helper
# -----------------------------
MEMORY_THRESHOLD = 0.6
REMINDER_COOLDOWN = timedelta(minutes=30)

def maybe_notify(concept, memory_score, graph):
    now = datetime.now()
    last_reminded_str = graph.nodes[concept].get('last_reminded_time')
    next_review_str = graph.nodes[concept].get('next_review_time')

    try:
        last_reminded = datetime.fromisoformat(last_reminded_str) if last_reminded_str else now - REMINDER_COOLDOWN
    except:
        last_reminded = now - REMINDER_COOLDOWN

    try:
        next_review = datetime.fromisoformat(next_review_str) if next_review_str else now
    except:
        next_review = now

    if memory_score < MEMORY_THRESHOLD and (now - last_reminded >= REMINDER_COOLDOWN):
        notification.notify(
            title="Time to Review!",
            message=f"Concept: {concept}\nMemory Score: {memory_score:.2f}",
            timeout=5
        )
        graph.nodes[concept]['last_reminded_time'] = now.isoformat()
        graph.nodes[concept]['next_review_time'] = (now + timedelta(hours=1)).isoformat()

# -----------------------------
# Tracker loop
# -----------------------------
def track_loop(stop_event: Event = None):
    if stop_event is None:
        stop_event = Event()

    init_db()
    init_multi_modal_db()
    init_memory_decay_db()
    kb_listener, ms_listener = start_listeners()

    ocr_counter = audio_counter = webcam_counter = save_counter = 0
    latest_ocr, latest_audio, latest_attention, latest_interaction = {}, "silence", 0, 0
    face_detector = FaceDetector()
    SAVE_INTERVAL = 300
    G = get_graph()

    try:
        while not stop_event.is_set():
            try:
                window, latest_interaction = get_active_window()
                log_session(window, latest_interaction)

                # -------- Audio --------
                audio_counter += TRACK_INTERVAL
                if audio_counter >= AUDIO_INTERVAL:
                    try:
                        latest_audio, audio_conf = classify_audio_live()
                        print(f"Audio -> {latest_audio} | Confidence: {audio_conf:.2f}")
                    except:
                        latest_audio, audio_conf = "unknown", 0.0
                    audio_counter = 0

                # -------- OCR --------
                ocr_counter += TRACK_INTERVAL
                if ocr_counter >= SCREENSHOT_INTERVAL:
                    try:
                        ocr_data = ocr_pipeline() or {}
                        latest_ocr = ocr_data.get('keywords', {}) or {}
                        safe_ocr = {}
                        for kw, info in latest_ocr.items():
                            if isinstance(info, dict):
                                safe_ocr[str(kw)] = {"score": float(info.get("score", 0.5)), "count": int(info.get("count", 1))}
                            else:
                                safe_ocr[str(kw)] = {"score": float(info), "count": 1}
                        latest_ocr = safe_ocr

                        if latest_ocr:
                            print(f"OCR Keywords: {latest_ocr}")
                            add_concepts(list(latest_ocr.keys()))
                        else:
                            print("OCR Keywords: None")
                    except Exception as e:
                        print(f"OCR error: {e}")
                        latest_ocr = {}
                    ocr_counter = 0
                    G = get_graph()

                    # -------- Memory & Reminders --------
                    for concept, info in latest_ocr.items():
                        try:
                            if concept not in G.nodes:
                                add_concepts([concept])
                                G = get_graph()

                            last_review = G.nodes[concept].get('last_review')
                            if isinstance(last_review, str):
                                try: last_review = datetime.fromisoformat(last_review)
                                except: last_review = datetime.now()
                            elif last_review is None: last_review = datetime.now()

                            lambda_val = 0.1
                            intent_conf = float(G.nodes[concept].get('intent_conf', 1.0))
                            attention_score = int(latest_attention or 0)
                            audio_conf = 1.0
                            kw_score = float(info.get("score", 0.5))
                            count = int(info.get("count", 1))

                            mem_score = compute_memory_score(
                                last_review, lambda_val, intent_conf, attention_score, audio_conf
                            )

                            mem_score = float(mem_score) * min(1.0, kw_score + 0.5)
                            mem_score = mem_score * min(1.5, 1 + 0.05 * (count - 1))

                            next_review = schedule_next_review(last_review, mem_score, lambda_val)

                            G.nodes[concept]['memory_score'] = float(mem_score)
                            G.nodes[concept]['next_review_time'] = next_review.isoformat() if isinstance(next_review, datetime) else str(next_review)
                            G.nodes[concept]['last_review'] = datetime.now().isoformat()
                            G.nodes[concept]['intent_conf'] = float(intent_conf)

                            maybe_notify(concept, mem_score, G)
                            _ = log_forgetting_curve(concept, last_review, observed_usage=count)
                        except Exception as e:
                            print(f"Error updating memory for {concept}: {e}")

                # -------- Webcam --------
                webcam_counter += TRACK_INTERVAL
                if webcam_counter >= WEBCAM_INTERVAL and USER_ALLOW_WEBCAM:
                    try:
                        frame = webcam_pipeline()
                        faces, num_faces = face_detector.detect_faces(frame)
                        latest_attention = int(num_faces)
                        print(f"Faces detected: {num_faces}")
                    except:
                        latest_attention = 0
                    webcam_counter = 0

                # -------- Intent --------
                intent_data = predict_intent_live(
                    latest_ocr, latest_audio, latest_attention, latest_interaction, use_webcam=USER_ALLOW_WEBCAM
                )
                print(f"Intent -> {intent_data['intent_label']} | Confidence: {intent_data['confidence']:.2f}")

                # Add edges safely
                try:
                    add_edges(latest_ocr, latest_audio, intent_data.get('intent_label', 'unknown'))
                except Exception as e:
                    print(f"Failed to add edges: {e}")

                # -------- Multi-modal logging --------
                try:
                    memory_score = max([float(G.nodes[kw].get('memory_score', 0.0)) for kw in latest_ocr.keys()] or [0.0])
                    log_multi_modal(
                        window, latest_ocr, latest_audio, latest_attention,
                        latest_interaction, intent_data.get('intent_label', 'unknown'),
                        float(intent_data.get('confidence', 0.0)),
                        memory_score=memory_score
                    )
                except Exception as e:
                    print(f"Failed multi-modal log: {e}")

                # -------- Periodic Knowledge Graph Save --------
                save_counter += TRACK_INTERVAL
                if save_counter >= SAVE_INTERVAL:
                    save_knowledge_graph()
                    save_counter = 0

                time.sleep(TRACK_INTERVAL)

            except KeyboardInterrupt:
                print("Tracker stopped by user (KeyboardInterrupt).")
                break
            except Exception as e:
                print(f"Unexpected loop error: {e}")
                time.sleep(TRACK_INTERVAL)
    finally:
        save_knowledge_graph()
        try:
            kb_listener.stop()
            ms_listener.stop()
        except:
            pass

# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    ask_user_permissions()
    track_loop()
