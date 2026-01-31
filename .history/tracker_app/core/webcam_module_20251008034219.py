"""
Webcam Module (IEEE-Ready v2)
-----------------------------
- Captures webcam frames and computes attention score.
- Handles missing predictor, unavailable webcam, or invalid frames safely.
- Uses dlib facial landmarks to compute eye aspect ratio (EAR).
"""

import cv2
import dlib
from imutils import face_utils
import numpy as np
import logging
from typing import Dict, List, Optional

# -----------------------------
# LOGGER SETUP
# -----------------------------
logging.basicConfig(
    filename="logs/webcam_module.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Ensure logs directory exists
import os
if not os.path.exists("logs"):
    os.makedirs("logs", exist_ok=True)

# -----------------------------
# Load face detector & landmarks predictor
# -----------------------------
detector = dlib.get_frontal_face_detector()
predictor_path = "core/shape_predictor_68_face_landmarks.dat"
predictor: Optional[dlib.shape_predictor] = None

try:
    predictor = dlib.shape_predictor(predictor_path)
    logging.info(f"dlib predictor loaded from {predictor_path}.")
except Exception:
    logging.warning(f"dlib predictor not found at {predictor_path}. Webcam attention will be disabled.")
    predictor = None

# -----------------------------
# EAR computation
# -----------------------------
def eye_aspect_ratio(eye: np.ndarray) -> float:
    """Compute EAR to detect blinks"""
    try:
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])
        C = np.linalg.norm(eye[0] - eye[3])
        ear = (A + B) / (2.0 * C)
        return float(ear)
    except Exception as e:
        logging.error(f"[WebcamModule] EAR computation failed: {e}")
        return 0.0

def compute_attention_score(ear_values: List[float]) -> float:
    """Convert EAR & blink frequency into attentiveness score"""
    try:
        if len(ear_values) == 0:
            return 0.0
        avg_ear = np.mean(ear_values)
        score = min(max((avg_ear - 0.18) * 500, 0), 100)  # Scale 0-100
        return float(score)
    except Exception as e:
        logging.error(f"[WebcamModule] Attention score computation failed: {e}")
        return 0.0

# -----------------------------
# Webcam pipeline
# -----------------------------
def webcam_pipeline(num_frames: int = 10) -> Dict[str, float]:
    """
    Capture webcam frames and compute attention score.
    Returns 0 if no face detected or predictor not loaded.
    """
    if predictor is None:
        logging.warning("[WebcamModule] Predictor not loaded. Returning 0 attention score.")
        return {"attentiveness_score": 0.0}

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logging.warning("[WebcamModule] Webcam not available.")
        return {"attentiveness_score": 0.0}

    ear_list: List[float] = []

    for _ in range(num_frames):
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        # Ensure proper 8-bit image
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
        if len(frame.shape) == 2:  # grayscale -> BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.shape[2] == 4:  # BGRA -> BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        try:
            faces = detector(gray)
        except Exception as e:
            logging.error(f"[WebcamModule] dlib detection error: {e}")
            continue

        for face in faces:
            try:
                shape = predictor(gray, face)
                shape = face_utils.shape_to_np(shape)
                leftEye = shape[42:48]
                rightEye = shape[36:42]
                leftEAR = eye_aspect_ratio(leftEye)
                rightEAR = eye_aspect_ratio(rightEye)
                ear = (leftEAR + rightEAR) / 2.0
                ear_list.append(ear)
            except Exception as e:
                logging.error(f"[WebcamModule] Face landmark processing failed: {e}")
                continue

    cap.release()
    cv2.destroyAllWindows()

    attention_score = compute_attention_score(ear_list) if ear_list else 0.0
    logging.info(f"[WebcamModule] Computed attentiveness score: {attention_score:.2f}")
    return {"attentiveness_score": attention_score}

# -----------------------------
# Self-test / demo
# -----------------------------
if __name__ == "__main__":
    result = webcam_pipeline()
    print("Attention Score:", result['attentiveness_score'])
