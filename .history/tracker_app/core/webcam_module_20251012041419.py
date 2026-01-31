# ==========================================================
# core/webcam_module.py | Fixed version (IEEE safe)
# ==========================================================
import cv2
import dlib
import numpy as np
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] [WebcamModule] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# -----------------------------
# Face detection + attentiveness
# -----------------------------
class FaceDetector:
    def __init__(self, predictor_path: str = "core/shape_predictor_68_face_landmarks.dat"):
        try:
            self.detector = dlib.get_frontal_face_detector()
            self.predictor = dlib.shape_predictor(predictor_path)
            logger.info(f"dlib predictor loaded from {predictor_path}.")
        except Exception as e:
            logger.error(f"Failed to load dlib predictor: {e}")
            self.detector = None
            self.predictor = None

    def detect_faces(self, frame: Optional[np.ndarray]):
        if frame is None:
            return [], 0
        try:
            if len(frame.shape) == 2:  # already grayscale
                gray = frame
            else:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rects = self.detector(gray)
            return rects, len(rects)
        except Exception as e:
            logger.error(f"dlib detection error: {e}")
            return [], 0


def compute_attentiveness(faces_count: int) -> float:
    """
    Simplified attentiveness heuristic: 1 if faces detected, else 0.
    """
    return 1.0 if faces_count > 0 else 0.0


def webcam_pipeline(return_dict: bool = True) -> Dict[str, Any] | np.ndarray:
    """
    Captures webcam frame, detects faces, and returns attentiveness score.
    Returns dict if return_dict=True, else returns just the numpy frame.
    """
    cap = None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Webcam not accessible.")
            return {"frame": None, "attentiveness": 0.0}

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            logger.error("Failed to capture frame from webcam.")
            return {"frame": None, "attentiveness": 0.0}

        # Ensure RGB 8-bit
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
        if frame.ndim == 3 and frame.shape[2] == 3:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

        # Face detection
        fd = FaceDetector()
        rects, count = fd.detect_faces(frame_rgb)
        attentiveness_score = compute_attentiveness(count)

        logger.info(f"Computed attentiveness score: {attentiveness_score:.2f}")

        result = {
            "frame": frame_rgb,
            "attentiveness": attentiveness_score,
            "faces_detected": count
        }
        return result if return_dict else frame_rgb

    except Exception as e:
        logger.error(f"Webcam pipeline failed: {e}")
        return {"frame": None, "attentiveness": 0.0}

    finally:
        if cap is not None:
            cap.release()
            cv2.destroyAllWindows()
