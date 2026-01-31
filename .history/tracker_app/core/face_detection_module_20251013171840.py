# ==========================================================
# core/face_detection_module_v4.py | IEEE v4 Async
# ==========================================================
"""
Face Detection Module v4 (IEEE-ready Async)
-------------------------------------------
- Fully async webcam capture & face detection
- Dlib-based frontal face detector
- Returns structured attention and confidence scores
- Fault-tolerant with safe fallback if webcam unavailable
- Scales attention score based on max_faces
- Compatible with FusionPipelineV4 & SessionManagerV4
"""

import cv2
import dlib
import asyncio
import logging
from threading import Thread, Event
from typing import Dict, Optional
import time
import numpy as np

# ----------------------------- Logger Setup -----------------------------
logger = logging.getLogger("FaceDetectionV4")
if not logger.handlers:
    handler = logging.FileHandler("logs/face_detection_v4.log")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ----------------------------- Face Detector Class -----------------------------
class FaceDetector:
    def __init__(self, camera_index: int = 0, resize_factor: float = 0.5, max_faces: int = 5):
        self.camera_index = camera_index
        self.resize_factor = resize_factor
        self.max_faces = max_faces
        self.detector: Optional[dlib.fhog_object_detector] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.latest_attention: Optional[int] = 0
        self._stop_event = Event()
        self.thread: Optional[Thread] = None
        self._initialize_detector()

    def _initialize_detector(self):
        try:
            self.detector = dlib.get_frontal_face_detector()
            logger.info("Dlib face detector loaded successfully.")
        except Exception as e:
            self.detector = None
            logger.error(f"Failed to initialize dlib detector: {e}")

    def _capture_loop(self):
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                logger.warning("Webcam could not be opened.")
                self.latest_attention = None
                return
        except Exception as e:
            logger.error(f"Failed to initialize webcam: {e}")
            self.latest_attention = None
            return

        while not self._stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.latest_attention = None
                continue

            # Optional downscale
            frame_small = cv2.resize(frame, (0, 0), fx=self.resize_factor, fy=self.resize_factor)

            try:
                rgb_frame = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)
                faces = self.detector(rgb_frame, 0) if self.detector else []
                self.latest_attention = len(faces)
            except Exception as e:
                logger.warning(f"Face detection error: {e}")
                self.latest_attention = None

    def start_async(self):
        """Start asynchronous webcam capture and face detection."""
        if self.thread is None:
            self._stop_event.clear()
            self.thread = Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            logger.info("Async face detection started.")

    def stop_async(self):
        """Stop async capture and release resources."""
        self._stop_event.set()
        if self.thread:
            self.thread.join()
            self.thread = None
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info("Async face detection stopped.")

    def get_latest_result(self) -> Dict[str, Optional[float]]:
        """Return structured attention output for tracker."""
        score = self.latest_attention
        if score is None:
            return {"attention_score": None, "confidence": 0.0, "reason": "Webcam unavailable"}
        confidence = min(1.0, score / float(self.max_faces))
        reason = "Faces detected" if score > 0 else "No faces detected"
        return {"attention_score": score, "confidence": confidence, "reason": reason}

# ----------------------------- Async Wrapper -----------------------------
async def async_detect_face(detector: FaceDetector) -> Dict[str, Optional[float]]:
    return await asyncio.to_thread(detector.get_latest_result)

# ----------------------------- Self-Test -----------------------------
def webcam_test(duration_sec: int = 10, display: bool = False):
    detector = FaceDetector()
    detector.start_async()
    start_time = time.time()
    while time.time() - start_time < duration_sec:
        result = detector.get_latest_result()
        if display:
            print(result)
        time.sleep(0.5)
    detector.stop_async()
    logger.info("Webcam test finished.")

if __name__ == "__main__":
    webcam_test(duration_sec=15, display=True)
