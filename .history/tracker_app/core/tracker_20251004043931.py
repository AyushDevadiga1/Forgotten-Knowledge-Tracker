# core/tracker.py

import time
import sqlite3
from pynput import keyboard, mouse
import win32gui
from datetime import datetime, timedelta
import json
import pickle
import os

from core.db_module import init_db, init_multi_modal_db
from config import DB_PATH, TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL, USER_ALLOW_WEBCAM
from core.ocr_module import ocr_pipeline
from core.audio_module import record_audio, extract_features as audio_extract_features
from core.webcam_module import webcam_pipeline
from core.intent_module import extract_features as intent_extract_features,predict_intent
from core.knowledge_graph import add_concepts, get_graph,
from core.memory_model import compute_memory_score, schedule_next_review
from plyer import notification
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
    title = win32gui.GetWindowText(hwnd)
    interaction_rate = keyboard_events + mouse_events
    return title, interaction_rate

# -----------------------------
# Log session to DB
# -----------------------------
def log_session(window_title, interaction_rate):
    global keyboard_events, mouse_events
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    app_name = window_title.split(" - ")[-1] if " - " in window_title else window_title

    # Ensure native Python types
    interaction_rate = int(interaction_rate)

    c.execute("""INSERT INTO sessions 
                 (start_ts, end_ts, app_name, window_title, interaction_rate) 
                 VALUES (?, ?, ?, ?, ?)""",
              (ts, ts, app_name, window_title, interaction_rate))
    conn.commit()
    conn.close()

    keyboard_events = 0
    mouse_events = 0
    print(f"Logged: {app_name}, Interaction: {interaction_rate}")

# -----------------------------
# Log multi-modal data
# -----------------------------
# -----------------------------
# Safe Multi-Modal Logging
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

    c.execute('''
        INSERT INTO multi_modal_logs
        (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp,
        window,
        json.dumps(ocr_data_to_store),
        audio_label,
        attention_score,
        interaction_rate,
        intent_label,
        intent_confidence,
        float(memory_score)
    ))

    conn.commit()
    conn.close()



# -----------------------------
# Persist knowledge graph
# -----------------------------
def save_knowledge_graph():
    G = get_graph()
    with open("data/knowledge_graph.pkl", "wb") as f:
        pickle.dump(G, f)

# -----------------------------
# Predict audio
# -----------------------------
def classify_audio_live():
    audio = record_audio()
    if audio_clf:
        features = audio_extract_features(audio).reshape(1, -1)
        label = audio_clf.predict(features)[0]
        confidence = max(audio_clf.predict_proba(features)[0])
        return label, confidence
    else:
        return "unknown", 0.0

# -----------------------------
# Predict intent
# -----------------------------
def predict_intent_live(ocr_keywords, audio_label, attention_score, interaction_rate):
    """Predict intent safely using trained classifier and fallback rules."""
    try:
        # Ensure numeric types
        attention_score = int(attention_score)
        interaction_rate = int(interaction_rate)

        features = intent_extract_features(
            ocr_keywords, audio_label, attention_score, interaction_rate, use_webcam=USER_ALLOW_WEBCAM
        )

        if intent_clf and intent_label_map:
            idx = int(intent_clf.predict(features)[0])
            confidence = float(max(intent_clf.predict_proba(features)[0]))

            # Correct usage of LabelEncoder
            label = intent_label_map.inverse_transform([idx])[0]

            return {"intent_label": label, "confidence": confidence}

        else:
            # fallback rules
            if audio_label == "speech" and interaction_rate > 5:
                if USER_ALLOW_WEBCAM and attention_score > 50:
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
# Tracker loop (updated)
# -----------------------------
def track_loop():
    init_db()
    init_multi_modal_db()
    init_memory_decay_db()
    start_listeners()

    ocr_counter = 0
    audio_counter = 0
    webcam_counter = 0
    save_counter = 0

    latest_ocr = {}
    latest_audio = "silence"
    latest_attention = 0
    latest_interaction = 0

    face_detector = FaceDetector()
    MEMORY_THRESHOLD = 0.6
    SAVE_INTERVAL = 300  # save knowledge graph every 5 minutes

    while True:
        try:
            # -------- Active Window & Logging --------
            window, latest_interaction = get_active_window()
            log_session(window, latest_interaction)

            # -------- OCR --------
            ocr_counter += TRACK_INTERVAL
            if ocr_counter >= SCREENSHOT_INTERVAL:
                ocr_data = ocr_pipeline()
                latest_ocr = ocr_data.get('keywords', {}) or {}

                # Safe conversion
                safe_ocr = {}
                for kw, info in latest_ocr.items():
                    if isinstance(info, dict):
                        safe_ocr[str(kw)] = {
                            "score": float(info.get("score", 0.5)),
                            "count": int(info.get("count", 1))
                        }
                    else:
                        safe_ocr[str(kw)] = {"score": float(info), "count": 1}
                latest_ocr = safe_ocr

                if latest_ocr:
                    print(f"OCR Keywords: {latest_ocr}")
                    add_concepts(list(latest_ocr.keys()))
                else:
                    print("OCR Keywords: None")

                ocr_counter = 0

                # -------- Memory Modeling & Knowledge Graph --------
                G = get_graph()
                for concept, info in latest_ocr.items():
                    kw_score = float(info.get("score", 0.5))
                    count = int(info.get("count", 1))

                    last_review = G.nodes[concept].get('last_review', datetime.now())
                    lambda_val = 0.1
                    intent_conf = float(G.nodes[concept].get('intent_conf', 1.0))
                    attention_score = int(latest_attention)
                    audio_conf = 1.0

                    mem_score = compute_memory_score(
                        last_review, lambda_val, intent_conf, attention_score, audio_conf
                    )

                    # Boosts
                    mem_score *= min(1.0, kw_score + 0.5)
                    mem_score *= min(1.5, 1 + 0.05 * (count - 1))

                    next_review = schedule_next_review(last_review, mem_score, lambda_val)

                    # Save in graph
                    G.nodes[concept]['memory_score'] = mem_score
                    G.nodes[concept]['next_review_time'] = next_review
                    G.nodes[concept]['last_review'] = datetime.now()
                    G.nodes[concept]['intent_conf'] = intent_conf

                    # Send reminder if memory low
                    if mem_score < MEMORY_THRESHOLD or next_review <= datetime.now():
                        notification.notify(
                            title="Time to Review!",
                            message=f"Concept: {concept}\nMemory Score: {mem_score:.2f}",
                            timeout=5
                        )
                        G.nodes[concept]['next_review_time'] = datetime.now() + timedelta(hours=1)

                    # -------- Forgetting Curve Logging --------
                    t_hours = (datetime.now() - last_review).total_seconds() / 3600
                    pred_recall = forgetting_curve(t_hours, s=1.25)

                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO memory_decay (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (concept, last_review.strftime("%Y-%m-%d %H:%M:%S"), pred_recall, count, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()

                # Build knowledge graph edges
                add_edges(latest_ocr, latest_audio, intent_data['intent_label'])

            # -------- Audio --------
            audio_counter += TRACK_INTERVAL
            if audio_counter >= AUDIO_INTERVAL:
                latest_audio, audio_conf = classify_audio_live()
                print(f"Audio -> {latest_audio} | Confidence: {audio_conf:.2f}")
                audio_counter = 0

            # -------- Webcam --------
            webcam_counter += TRACK_INTERVAL
            if webcam_counter >= WEBCAM_INTERVAL and USER_ALLOW_WEBCAM:
                try:
                    frame = webcam_pipeline()
                    faces, num_faces = face_detector.detect_faces(frame)
                    latest_attention = int(num_faces)
                    print(f"Faces detected: {num_faces}")
                except Exception as e:
                    print(f"Webcam error (ignored): {e}")
                    latest_attention = 0
                webcam_counter = 0

            # -------- Intent --------
            intent_data = predict_intent(
                latest_ocr,
                latest_audio,
                latest_attention,
                latest_interaction,
                use_webcam=USER_ALLOW_WEBCAM
            )
            print(f"Intent -> {intent_data['intent_label']} | Confidence: {intent_data['confidence']:.2f}")

            # -------- Log Multi-Modal Data including memory score --------
            log_multi_modal(
                window,
                latest_ocr,
                latest_audio,
                latest_attention,
                latest_interaction,
                intent_data['intent_label'],
                float(intent_data['confidence']),
                memory_score=max([G.nodes[kw]['memory_score'] for kw in latest_ocr.keys()]) if latest_ocr else 0.0
            )

            # -------- Periodic Knowledge Graph Save --------
            save_counter += TRACK_INTERVAL
            if save_counter >= SAVE_INTERVAL:
                save_knowledge_graph()
                save_counter = 0

            time.sleep(TRACK_INTERVAL)

        except KeyboardInterrupt:
            print("Tracker stopped by user.")
            save_knowledge_graph()
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(TRACK_INTERVAL)

# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    ask_user_permissions()
    track_loop()
