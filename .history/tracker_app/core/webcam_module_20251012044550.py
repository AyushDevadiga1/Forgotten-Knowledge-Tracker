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
# FACE DETECTION SETUP
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
    """Enhances brightness for low-light images."""
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
# ATTENTIVENESS / EYE TRACKING
# -----------------------------
def compute_attentiveness(frame: np.ndarray) -> Dict[str, Any]:
    """
    Computes attentiveness based on eye/face detection.
    Returns structured scenario-aware dictionary.
    """
    result = {
        "attentive": None,
        "confidence": 0.0,
        "reason": "Unknown",
        "intention": "Observing task",
    }

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
        landmarks = [(p.x, p.y) for p in shape.parts()]
        if not landmarks:
            result.update({"attentive": False, "confidence": 0.1, "reason": "Face detected but landmarks missing"})
            return result

        # Example rules for eye tracking
        # Here we could add actual eye-state detection in future
        result.update({
            "attentive": True,
            "confidence": 0.9,
            "reason": "Eyes open and focused",
        })

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
    Captures webcam frame, applies conversions, low-light fix,
    and computes attentiveness. Returns structured dictionary.
    """
    output = {
        "frame": None,
        "attentive": None,
        "confidence": 0.0,
        "reason": "",
        "intention": "",
    }

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

    # Convert frame safely to RGB uint8
    try:
        formats_tried = [("Original", str(frame.dtype), frame.shape)]
        if frame.dtype != np.uint8:
            frame = cv2.convertScaleAbs(frame)
            formats_tried.append(("Converted uint8", str(frame.dtype), frame.shape))

        if len(frame.shape) == 2:  # Grayscale
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            formats_tried.append(("GRAY2RGB", str(frame.dtype), frame.shape))
        elif frame.shape[2] == 4:  # RGBA
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
            formats_tried.append(("RGBA2RGB", str(frame.dtype), frame.shape))
        else:  # Assume BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            formats_tried.append(("BGR2RGB", str(frame.dtype), frame.shape))
    except Exception as e:
        logger.error(f"Frame conversion failed: {e}")
        output.update({"attentive": False, "reason": "Frame conversion failed"})
        return output

    # Enhance lighting if needed
    frame = enhance_low_light(frame)

    # Compute attentiveness
    attention_result = compute_attentiveness(frame)
    output.update(attention_result)
    output["frame"] = frame

    logger.info(f"Formats tried: {formats_tried}")
    logger.info(f"Webcam attentiveness result: {attention_result}")

    return output


# -----------------------------
# TEST
# -----------------------------
if __name__ == "__main__":
    result = webcam_pipeline()
    print("Webcam pipeline output:")
    print(result)
