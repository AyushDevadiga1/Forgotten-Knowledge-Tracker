# ==========================================================
# core/webcam_module.py
# ==========================================================
"""
Webcam Module (IEEE-Ready v2)
-----------------------------
Handles webcam capture, face & eye tracking, head orientation,
occlusion detection, low-light enhancement, and attentiveness scoring.
Returns structured multi-modal output for fusion with other modules.
"""

import cv2
import numpy as np
import logging
from typing import Dict, Any, Optional
from core.face_detection_module import FaceDetector
import dlib

# -----------------------------
# LOGGER SETUP
# -----------------------------
logging.basicConfig(
    filename="logs/webcam_module.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [WebcamModule] %(message)s",
)
logger = logging.getLogger(__name__)

# -----------------------------
# INITIALIZE DETECTORS
# -----------------------------
face_detector = FaceDetector()
try:
    predictor = dlib.shape_predictor("core/shape_predictor_68_face_landmarks.dat")
    logger.info("dlib shape predictor loaded successfully.")
except Exception as e:
    predictor = None
    logger.error(f"Failed to load dlib predictor: {e}")

# -----------------------------
# LOW-LIGHT ENHANCEMENT
# -----------------------------
def enhance_low_light(frame: np.ndarray) -> np.ndarray:
    try:
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        h, s, v = cv2.split(hsv)
        avg_brightness = np.mean(v)
        if avg_brightness < 60:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            v = clahe.apply(v)
            frame = cv2.cvtColor(cv2.merge((h, s, v)), cv2.COLOR_HSV2RGB)
        return frame
    except Exception as e:
        logger.error(f"Low-light enhancement failed: {e}")
        return frame

# -----------------------------
# EYE & BLINK DETECTION
# -----------------------------
def eye_aspect_ratio(eye_points: np.ndarray) -> float:
    A = np.linalg.norm(eye_points[1] - eye_points[5])
    B = np.linalg.norm(eye_points[2] - eye_points[4])
    C = np.linalg.norm(eye_points[0] - eye_points[3])
    return (A + B) / (2.0 * C)

def extract_eye_landmarks(shape) -> Dict[str, np.ndarray]:
    coords = np.array([[p.x, p.y] for p in shape.parts()])
    return {"left": coords[36:42], "right": coords[42:48]}

def detect_eye_state(shape) -> Dict[str, Any]:
    try:
        eyes = extract_eye_landmarks(shape)
        left_ear = eye_aspect_ratio(eyes["left"])
        right_ear = eye_aspect_ratio(eyes["right"])
        avg_ear = (left_ear + right_ear) / 2.0

        EAR_CLOSED = 0.2
        EAR_BLINK = 0.25

        if avg_ear < EAR_CLOSED:
            return {"attentive": False, "confidence": 0.9, "reason": "Eyes closed or micro-sleep"}
        elif avg_ear < EAR_BLINK:
            return {"attentive": True, "confidence": 0.6, "reason": "Blinking / momentary closure"}
        else:
            return {"attentive": True, "confidence": 0.95, "reason": "Eyes open and focused"}
    except Exception as e:
        logger.warning(f"Eye detection failed: {e}")
        return {"attentive": None, "confidence": 0.5, "reason": "Eye state unknown"}

# -----------------------------
# HEAD ORIENTATION
# -----------------------------
def head_orientation(shape) -> Dict[str, Any]:
    try:
        nose = np.array([shape.part(30).x, shape.part(30).y])
        left_eye_center = np.mean([[p.x, p.y] for p in shape.parts()[36:42]], axis=0)
        right_eye_center = np.mean([[p.x, p.y] for p in shape.parts()[42:48]], axis=0)
        horizontal_ratio = (nose[0] - left_eye_center[0]) / max(1.0, (right_eye_center[0] - left_eye_center[0]))

        if horizontal_ratio < 0.35:
            return {"attentive": False, "confidence": 0.7, "reason": "Head turned left"}
        elif horizontal_ratio > 0.65:
            return {"attentive": False, "confidence": 0.7, "reason": "Head turned right"}
        else:
            return {"attentive": True, "confidence": 0.9, "reason": "Head facing forward"}
    except Exception as e:
        logger.warning(f"Head orientation failed: {e}")
        return {"attentive": None, "confidence": 0.5, "reason": "Head pose unknown"}

# -----------------------------
# ATTENTIVENESS COMPUTATION
# -----------------------------
def compute_attentiveness(frame: np.ndarray) -> Dict[str, Any]:
    result = {"attentive": None, "confidence": 0.0, "reason": "Unknown", "intention": "Observing task"}
    try:
        faces, num_faces = face_detector.detect_faces(frame)
        if num_faces == 0:
            result.update({"attentive": None, "confidence": 0.0, "reason": "No face detected"})
            return result

        if predictor is None:
            result.update({"attentive": None, "confidence": 0.5, "reason": "Predictor not loaded"})
            return result

        shape = predictor(frame, faces[0])

        eye_result = detect_eye_state(shape)
        head_result = head_orientation(shape)

        # Combine results conservatively
        if eye_result["attentive"] is False or head_result["attentive"] is False:
            attentive = False
            confidence = min(eye_result["confidence"], head_result["confidence"])
            reason = f"{eye_result['reason']} + {head_result['reason']}"
        else:
            attentive = True
            confidence = min(1.0, eye_result["confidence"] + head_result["confidence"] - 0.5)
            reason = f"{eye_result['reason']} + {head_result['reason']}"

        result.update({"attentive": attentive, "confidence": confidence, "reason": reason})
        return result

    except Exception as e:
        logger.error(f"Attentiveness computation failed: {e}")
        result.update({"attentive": False, "confidence": 0.0, "reason": f"Detection error: {e}"})
        return result

# ==========================================================
# core/webcam_module.py (with temporal smoothing)
# ==========================================================

from collections import deque

# -----------------------------
# TEMPORAL SMOOTHING SETTINGS
# -----------------------------
FRAME_HISTORY = 5  # Number of frames to average over
_attn_history: deque = deque(maxlen=FRAME_HISTORY)

def smooth_attentiveness(attn_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Smooths attentiveness over the last FRAME_HISTORY frames.
    Returns weighted average confidence and majority attentive state.
    """
    _attn_history.append(attn_result)
    if not _attn_history:
        return attn_result

    # Majority vote for attentive
    attentive_votes = [1 if f["attentive"] else 0 for f in _attn_history if f["attentive"] is not None]
    attentive_state = True if sum(attentive_votes) > len(attentive_votes)/2 else False

    # Average confidence
    conf_values = [f["confidence"] for f in _attn_history]
    avg_conf = float(np.mean(conf_values)) if conf_values else attn_result["confidence"]

    # Combine reasons
    reasons = [f["reason"] for f in _attn_history if f.get("reason")]
    combined_reason = " | ".join(reasons[-FRAME_HISTORY:])  # last FRAME_HISTORY reasons

    smoothed_result = attn_result.copy()
    smoothed_result.update({
        "attentive": attentive_state,
        "confidence": avg_conf,
        "reason": combined_reason
    })
    return smoothed_result

# -----------------------------
# UPDATED WEBCAM PIPELINE
# -----------------------------
def webcam_pipeline_smoothed() -> Dict[str, Any]:
    output = {"frame": None, "attentive": None, "confidence": 0.0, "reason": "", "intention": ""}

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        output.update({"attentive": False, "reason": "Webcam not accessible"})
        logger.error("Webcam not accessible.")
        return output

    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        output.update({"attentive": False, "reason": "Failed to capture frame"})
        logger.error("Failed to capture frame.")
        return output

    # RGB conversion & low-light enhancement
    try:
        if frame.dtype != np.uint8:
            frame = cv2.convertScaleAbs(frame)
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        elif frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
        else:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    except Exception as e:
        logger.error(f"Frame conversion failed: {e}")
        output.update({"attentive": False, "reason": "Frame conversion failed"})
        return output

    frame = enhance_low_light(frame)
    attn_result = compute_attentiveness(frame)

    # Apply temporal smoothing
    smoothed_result = smooth_attentiveness(attn_result)

    output.update(smoothed_result)
    output["frame"] = frame
    return output

# -----------------------------
# TEST
# -----------------------------
if __name__ == "__main__":
    for _ in range(10):
        result = webcam_pipeline()
        print(result)
