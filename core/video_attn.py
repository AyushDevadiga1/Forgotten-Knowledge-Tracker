# video_attn.py - Optimized for FKT
import cv2
import mediapipe as mp
import time
import sqlite3
from config import DB_PATH, VIDEO_FRAME_INTERVAL

mp_face = mp.solutions.face_mesh
_face_mesh = None

def _init_face_mesh():
    global _face_mesh
    if _face_mesh is None:
        _face_mesh = mp_face.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    return _face_mesh

def get_eye_aspect_ratio(landmarks):
    # Placeholder for eye aspect ratio
    return 0.3  # 0.0 (closed) → 1.0 (open)

def compute_attentiveness(frame):
    try:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_mesh = _init_face_mesh()
        results = face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]
            ear = get_eye_aspect_ratio(landmarks)
            attention_score = int(ear * 100)
            return attention_score, True
        else:
            return 0, False
    except Exception as e:
        print("[Video Error]", e)
        return 0, False

def log_attention(session_id, attention_score):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO video_logs (session_id, attentiveness_score) VALUES (?, ?)",
            (session_id, attention_score)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("[Video DB Error]", e)

def start_attention_tracking():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    retry_count = 0
    while not cap.isOpened() and retry_count < 10:
        print("[Video] Waiting for webcam...")
        time.sleep(1)
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        retry_count += 1

    if not cap.isOpened():
        print("[Video] Could not open webcam.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("[Video] Webcam attention tracking started...")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(VIDEO_FRAME_INTERVAL)
                continue

            score, detected = compute_attentiveness(frame)

            # Throttle logging to once every N frames
            if detected:
                print(f"[Video] Face detected! Attention: {score}")

            # Optional: log to DB
            # log_attention(session_id, score)

            time.sleep(VIDEO_FRAME_INTERVAL)

    except KeyboardInterrupt:
        print("[Video] Stopping webcam tracking...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
