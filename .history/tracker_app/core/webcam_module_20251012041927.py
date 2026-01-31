"""
webcam_module.py
----------------
Handles webcam frame capture, face detection, and attentiveness scoring.
Includes auto format correction and low-light fallback for robust use.
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
# LIGHT ENHANCEMENT UTILS
# -----------------------------
def enhance_low_light(frame: np.ndarray) -> np.ndarray:
    """Enhances brightness for low-light images."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    h, s, v = cv2.split(hsv)

    avg_brightness = np.mean(v)
    if avg_brightness < 60:
        logger.warning(f"Low light detected (brightness={avg_brightness:.2f}). Applying enhancement.")
        # CLAHE for adaptive brightness boost
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        v = clahe.apply(v)
        hsv = cv2.merge((h, s, v))
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    return frame


# -----------------------------
# ATTENTIVENESS SCORE
# -----------------------------
def compute_attentiveness(frame: np.ndarray) -> float:
    """Computes attentiveness based on face and landmark presence."""
    try:
        faces = detector(frame)
        if len(faces) == 0:
            logger.info("No faces detected.")
            return 0.0

        face = faces[0]
        shape = predictor(frame, face)
        landmarks = [(p.x, p.y) for p in shape.parts()]
        logger.info(f"Detected {len(landmarks)} facial landmarks.")

        return 1.0 if landmarks else 0.0
    except Exception as e:
        logger.error(f"dlib detection error: {e}")
        return 0.0


# -----------------------------
# MAIN PIPELINE
# -----------------------------
def webcam_pipeline() -> Dict[str, Any]:
    """Captures webcam frame and computes attentiveness."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Webcam not accessible.")
        return {"frame": None, "attentiveness": 0.0}

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        logger.error("Failed to capture frame.")
        return {"frame": None, "attentiveness": 0.0}

    # Try to convert frame to every common safe format
    formats_tried = []
    frame_result = None

    try:
        formats_tried.append(("Original", str(frame.dtype), frame.shape))

        # Convert to uint8 if not already
        if frame.dtype != np.uint8:
            frame = cv2.convertScaleAbs(frame)
            formats_tried.append(("Converted uint8", str(frame.dtype), frame.shape))

        # Try BGR → RGB
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_result = frame_rgb
            formats_tried.append(("BGR2RGB", str(frame_rgb.dtype), frame_rgb.shape))
        except Exception:
            pass

        # Try RGBA → RGB
        if frame_result is None and frame.shape[-1] == 4:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
            frame_result = frame_rgb
            formats_tried.append(("RGBA2RGB", str(frame_rgb.dtype), frame_rgb.shape))

        # Try grayscale → RGB
        if frame_result is None and len(frame.shape) == 2:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            frame_result = frame_rgb
            formats_tried.append(("GRAY2RGB", str(frame_rgb.dtype), frame_rgb.shape))

        if frame_result is None:
            logger.warning("Could not identify image format for webcam frame.")
            return {"frame": None, "attentiveness": 0.0}

        # Enhance lighting if too dark
        frame_final = enhance_low_light(frame_result)

        # Compute attentiveness
        attentiveness_score = compute_attentiveness(frame_final)

        logger.info(f"Conversion attempts: {formats_tried}")
        logger.info(f"Computed attentiveness score: {attentiveness_score:.2f}")

        return {"frame": frame_final, "attentiveness": attentiveness_score}

    except Exception as e:
        logger.error(f"Webcam pipeline failed: {e}")
        logger.info(f"Formats attempted: {formats_tried}")
        return {"frame": None, "attentiveness": 0.0}
