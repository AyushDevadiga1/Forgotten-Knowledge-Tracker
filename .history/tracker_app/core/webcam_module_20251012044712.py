"""
webcam_module.py
----------------
Handles webcam frame capture, face detection, eye tracking, and attentiveness scoring.
Includes auto format correction, low-light fallback, and scenario-aware outputs.
"""

import cv2
import dlib
import numpy as np
import logging
from typing import Dict, Any

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
# FACE & LANDMARK DETECTION
# -----------------------------
detector = dlib.get_frontal_face_detector()
predictor = None

try:
    predictor = dlib.shape_predictor("core/shape_predictor_68_face_landmarks.dat")
    logger.info("dlib predictor loaded from core/shape_predictor_68_face_landmarks.dat.")
except Exception as e:
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
            logger.warning(f"Low light detected (brightness={avg_brightness:.2f}). Applying enhancement.")
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            v = clahe.apply(v)
            frame = cv2.cvtColor(cv2.merge((h, s, v)), cv2.COLOR_HSV2RGB)
        return frame
    except Exception as e:
        logger.error(f"Low-light enhancement failed: {e}")
        return frame

# -----------------------------
# EYE STATE DETECTION
# -----------------------------
def eye_aspect_ratio(eye_points: np.ndarray) -> float:
    """Compute Eye Aspect Ratio (EAR) to detect blinking."""
    A = np.linalg.norm(eye_points[1] - eye_points[5])
    B = np.linalg.norm(eye_points[2] - eye_points[4])
    C = np.linalg.norm(eye_points[0] - eye_points[3])
    ear = (A + B) / (2.0 * C)
    return ear

def extract_eye_landmarks(shape) -> Dict[str, np.ndarray]:
    """Return numpy arrays for left and right eyes from landmarks."""
    coords = np.array([[p.x, p.y] for p in shape.parts()])
    left_eye = coords[36:42]
    right_eye = coords[42:48]
    return {"left": left_eye, "right": right_eye}

def detect_eye_state(shape) -> Dict[str, Any]:
    """
    Determines if eyes are open, closed, or blinking.
    Returns scenario-aware result.
    """
    eyes = extract_eye_landmarks(shape)
    left_ear = eye_aspect_ratio(eyes["left"])
    right_ear = eye_aspect_ratio(eyes["right"])
    avg_ear = (left_ear + right_ear) / 2.0

    # EAR thresholds (typical for dlib landmarks)
    EAR_CLOSED = 0.2
    EAR_BLINK = 0.25

    if avg_ear < EAR_CLOSED:
        return {"attentive": False, "confidence": 0.9, "reason": "Eyes closed or micro-sleep"}
    elif avg_ear < EAR_BLINK:
        return {"attentive": True, "confidence": 0.6, "reason": "Blinking / momentary closure"}
    else:
        return {"attentive": True, "confidence": 0.95, "reason": "Eyes open and focused"}

# -----------------------------
# ATTENTIVENESS
# -----------------------------
def compute_attentiveness(frame: np.ndarray) -> Dict[str, Any]:
    """
    Computes attentiveness using face and eye landmarks.
    Returns structured scenario-aware dictionary.
    """
    result = {"attentive": None, "confidence": 0.0, "reason": "Unknown", "intention": "Observing task"}

    try:
        faces = detector(frame)
        if len(faces) == 0:
            result.update({"attentive": False, "confidence": 0.0, "reason": "No face detected"})
            return result

        face = faces[0]
        if predictor is None:
            result.update({"attentive": None, "confidence": 0.5, "reason": "Predictor not loaded"})
            return result

        shape = predictor(frame, face)
        eye_result = detect_eye_state(shape)
        result.update(eye_result)
        return result

    except Exception as e:
        logger.error(f"dlib detection error: {e}")
        result.update({"attentive": False, "confidence": 0.0, "reason": f"Detection error: {e}"})
        return result

# -----------------------------
# WEBCAM PIPELINE
# -----------------------------
def webcam_pipeline() -> Dict[str, Any]:
    """
    Captures webcam frame, converts to RGB, enhances low-light,
    and computes attentiveness using eye tracking.
    """
    output = {"frame": None, "attentive": None, "confidence": 0.0, "reason": "", "intention": ""}

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Webcam not accessible.")
        output.update({"attentive": False, "reason": "Webcam not accessible"})
        return output

    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        logger.error("Failed to capture frame.")
        output.update({"attentive": False, "reason": "Failed to capture frame"})
        return output

    # Frame conversions
    try:
        if frame.dtype != np.uint8:
            frame = cv2.convertScaleAbs(frame)
        if len(frame.shape) == 2:  # Grayscale
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        elif frame.shape[2] == 4:  # RGBA
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
        else:  # Assume BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    except Exception as e:
        logger.error(f"Frame conversion failed: {e}")
        output.update({"attentive": False, "reason": "Frame conversion failed"})
        return output

    frame = enhance_low_light(frame)
    attention_result = compute_attentiveness(frame)
    output.update(attention_result)
    output["frame"] = frame

    logger.info(f"Webcam attentiveness result: {attention_result}")
    return output

# -----------------------------
# TEST
# -----------------------------
if __name__ == "__main__":
    result = webcam_pipeline()
    print("Webcam pipeline output:")
    print(result)
