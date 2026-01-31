# ==========================================================
# core/webcam_module.py | IEEE v4 Async Refactored
# ==========================================================
"""
Webcam Module (IEEE v4 Async)
-----------------------------
- Async FaceDetectorV4 for non-blocking capture
- Computes attentiveness using detector + eye/head metrics
- Low-light enhancement included
- Temporal smoothing over FRAME_HISTORY frames
- Returns structured dict for FusionPipelineV4:
  {
      "frame": np.ndarray,
      "attentive": bool,
      "confidence": float,
      "reason": str,
      "intention": str
  }
- Fully async-compatible & fault-tolerant
"""

import cv2
import numpy as np
import logging
from collections import deque
from typing import Dict, Any
import asyncio
from core.face_detection_module import FaceDetector
import dlib

# ----------------------------- Logger Setup -----------------------------
logging.basicConfig(
    filename="logs/webcam_module_v4.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [WebcamModuleV4] %(message)s",
)
logger = logging.getLogger(__name__)

# ----------------------------- Initialize Async Detector -----------------------------
face_detector = FaceDetectorV4()
face_detector.start_async()  # background capture

# ----------------------------- Dlib Predictor -----------------------------
try:
    predictor = dlib.shape_predictor("core/shape_predictor_68_face_landmarks.dat")
    logger.info("dlib shape predictor loaded successfully.")
except Exception as e:
    predictor = None
    logger.warning(f"Predictor not loaded: {e}")

# ----------------------------- Low-light Enhancement -----------------------------
def enhance_low_light(frame: np.ndarray) -> np.ndarray:
    try:
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        h, s, v = cv2.split(hsv)
        if np.mean(v) < 60:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            v = clahe.apply(v)
            frame = cv2.cvtColor(cv2.merge((h, s, v)), cv2.COLOR_HSV2RGB)
        return frame
    except Exception as e:
        logger.error(f"Low-light enhancement failed: {e}")
        return frame

# ----------------------------- Eye & Head Detection -----------------------------
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

def head_orientation(shape) -> Dict[str, Any]:
    try:
        nose = np.array([shape.part(30).x, shape.part(30).y])
        left_eye_center = np.mean([[p.x, p.y] for p in shape.parts()[36:42]], axis=0)
        right_eye_center = np.mean([[p.x, p.y] for p in shape.parts()[42:48]], axis=0)
        ratio = (nose[0] - left_eye_center[0]) / max(1.0, (right_eye_center[0] - left_eye_center[0]))
        if ratio < 0.35:
            return {"attentive": False, "confidence": 0.7, "reason": "Head turned left"}
        elif ratio > 0.65:
            return {"attentive": False, "confidence": 0.7, "reason": "Head turned right"}
        else:
            return {"attentive": True, "confidence": 0.9, "reason": "Head facing forward"}
    except Exception as e:
        logger.warning(f"Head orientation failed: {e}")
        return {"attentive": None, "confidence": 0.5, "reason": "Head pose unknown"}

def compute_attentiveness(frame: np.ndarray) -> Dict[str, Any]:
    """Compute fused attentiveness using predictor + face detection."""
    result = {"attentive": None, "confidence": 0.0, "reason": "Unknown", "intention": "Observing task"}
    try:
        if predictor:
            shape = predictor(frame, face_detector.get_face_rect(frame))
            eye_result = detect_eye_state(shape)
            head_result = head_orientation(shape)
            result["confidence"] = min(1.0, eye_result["confidence"] + head_result["confidence"] - 0.5)
            result["attentive"] = eye_result["attentive"] and head_result["attentive"]
            result["reason"] = f"{eye_result['reason']} + {head_result['reason']}"
        else:
            result.update(face_detector.get_latest_result())
        return result
    except Exception as e:
        logger.error(f"Attentiveness computation failed: {e}")
        return {"attentive": False, "confidence": 0.0, "reason": f"Detection error: {e}", "intention": "Observing task"}

# ----------------------------- Temporal Smoothing -----------------------------
FRAME_HISTORY = 5
_attn_history: deque = deque(maxlen=FRAME_HISTORY)

def smooth_attentiveness(attn_result: Dict[str, Any]) -> Dict[str, Any]:
    _attn_history.append(attn_result)
    votes = [1 if f["attentive"] else 0 for f in _attn_history if f["attentive"] is not None]
    attentive_state = sum(votes) > len(votes)/2
    avg_conf = float(np.mean([f["confidence"] for f in _attn_history]))
    combined_reason = " | ".join([f["reason"] for f in _attn_history if f.get("reason")])
    smoothed = attn_result.copy()
    smoothed.update({"attentive": attentive_state, "confidence": avg_conf, "reason": combined_reason})
    return smoothed

# ----------------------------- Async Webcam Pipeline -----------------------------
async def webcam_pipeline(num_frames: int = 5) -> Dict[str, Any]:
    output = {"frame": None, "attentive": None, "confidence": 0.0, "reason": "", "intention": "Observing task"}
    latest_frame = getattr(face_detector, "cap_frame", None)
    if latest_frame is None:
        output.update(face_detector.get_latest_result())
        return output

    frame = enhance_low_light(latest_frame)
    output["frame"] = frame

    attn_res = await asyncio.to_thread(compute_attentiveness, frame)
    smoothed = await asyncio.to_thread(smooth_attentiveness, attn_res)
    output.update(smoothed)
    return output

# ----------------------------- Self-Test -----------------------------
if __name__ == "__main__":
    import asyncio
    async def test():
        for _ in range(5):
            res = await webcam_pipeline()
            print(res)
            await asyncio.sleep(0.5)
    asyncio.run(test())
