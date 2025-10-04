# core/tracker.py

import time
import sqlite3
from pynput import keyboard, mouse
import win32gui
from datetime import datetime, timedelta
import json
import pickle

from core.db_module import init_db, init_multi_modal_db
from config import DB_PATH, TRACK_INTERVAL, SCREENSHOT_INTERVAL, AUDIO_INTERVAL, WEBCAM_INTERVAL, USER_ALLOW_WEBCAM
from core.ocr_module import ocr_pipeline
from core.audio_module import audio_pipeline
from core.webcam_module import webcam_pipeline
from core.intent_module import predict_intent
from core.knowledge_graph import add_concepts, get_graph
from core.memory_model import compute_memory_score, schedule_next_review
from plyer import notification
from core.face_detection_module import FaceDetector

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
def log_multi_modal(window, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute('''
        INSERT INTO multi_modal_logs
        (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp,
        window,
        json.dumps(ocr_keywords),  # store as JSON string
        audio_label,
        attention_score,
        interaction_rate,
        intent_label,
        intent_confidence
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
# Tracker loop
# -----------------------------
def track_loop():
    init_db()
    init_multi_modal_db()
    start_listeners()
    
    ocr_counter = 0
    audio_counter = 0
    webcam_counter = 0
    save_counter = 0

    latest_ocr = []
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
                latest_ocr = ocr_data.get('keywords', [])
                ocr_counter = 0

                if latest_ocr:
                    add_concepts(latest_ocr)

                # -------- Memory Modeling --------
                G = get_graph()
                for concept in latest_ocr:
                    last_review = G.nodes[concept].get('last_review', datetime.now())
                    lambda_val = 0.1
                    intent_conf = G.nodes[concept].get('intent_conf', 1.0)
                    attention_score = latest_attention
                    audio_conf = 1.0

                    mem_score = compute_memory_score(
                        last_review, lambda_val, intent_conf, attention_score, audio_conf
                    )
                    next_review = schedule_next_review(last_review, mem_score, lambda_val)

                    G.nodes[concept]['memory_score'] = mem_score
                    G.nodes[concept]['next_review_time'] = next_review

                    # -------- Reminders --------
                    now = datetime.now()
                    if mem_score < MEMORY_THRESHOLD or next_review <= now:
                        notification.notify(
                            title="Time to Review!",
                            message=f"Concept: {concept}\nMemory Score: {mem_score:.2f}",
                            timeout=5
                        )
                        G.nodes[concept]['next_review_time'] = now + timedelta(hours=1)

            # -------- Audio --------
            audio_counter += TRACK_INTERVAL
            if audio_counter >= AUDIO_INTERVAL:
                audio_data = audio_pipeline()
                latest_audio = audio_data.get('audio_label', 'silence')
                audio_counter = 0

            # -------- Webcam --------
            webcam_counter += TRACK_INTERVAL
            if webcam_counter >= WEBCAM_INTERVAL and USER_ALLOW_WEBCAM:
                try:
                    frame = webcam_pipeline()
                    faces, num_faces = face_detector.detect_faces(frame)
                    latest_attention = num_faces
                    print(f"Faces detected: {num_faces}")
                except Exception as e:
                    print(f"Webcam error (ignored): {e}")
                    latest_attention = 0
                webcam_counter = 0

            # -------- Intent --------
            intent_data = predict_intent(
                ocr_keywords=latest_ocr,
                audio_label=latest_audio,
                attention_score=latest_attention,
                interaction_rate=latest_interaction,
                use_webcam=USER_ALLOW_WEBCAM
            )
            print(f"Intent: {intent_data['intent_label']} | Confidence: {intent_data['confidence']:.2f}")

            # -------- Log Multi-Modal Data --------
            log_multi_modal(
                window,
                latest_ocr,
                latest_audio,
                latest_attention,
                latest_interaction,
                intent_data['intent_label'],
                intent_data['confidence']
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
