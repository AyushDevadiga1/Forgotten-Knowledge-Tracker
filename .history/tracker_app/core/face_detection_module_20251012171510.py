# core/face_detection_module.py
import cv2
import dlib
import time
from threading import Thread, Event
from typing import Dict, Tuple, Optional

class FaceDetector:
    def __init__(self, camera_index=0, resize_factor=0.5):
        self.camera_index = camera_index
        self.resize_factor = resize_factor
        self.detector = None
        self.cap = None
        self.latest_attention = 0
        self._stop_event = Event()
        self.thread: Optional[Thread] = None
        self._initialize_detector()

    def _initialize_detector(self):
        try:
            self.detector = dlib.get_frontal_face_detector()
            print("Face detector loaded successfully.")
        except Exception as e:
            self.detector = None
            print(f"Error loading face detector: {e}")

    def _capture_loop(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.camera_index)

        while not self._stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.latest_attention = None
                continue

            # Optional downscale for speed
            frame_small = cv2.resize(frame, (0, 0), fx=self.resize_factor, fy=self.resize_factor)

            # Detect faces
            try:
                rgb_frame = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)
                faces = self.detector(rgb_frame, 0) if self.detector else []
                self.latest_attention = len(faces)
            except Exception:
                self.latest_attention = None

    def start_async(self):
        """Start webcam capture and face detection in background."""
        self._stop_event.clear()
        if self.thread is None:
            self.thread = Thread(target=self._capture_loop, daemon=True)
            self.thread.start()

    def stop_async(self):
        """Stop background capture."""
        self._stop_event.set()
        if self.thread:
            self.thread.join()
            self.thread = None
        if self.cap:
            self.cap.release()
            self.cap = None

    def get_latest_result(self) -> Dict[str, Optional[float]]:
        """Return structured attention output for tracker integration."""
        score = self.latest_attention
        if score is None:
            return {"attention_score": None, "confidence": 0.0, "reason": "Webcam unavailable"}
        else:
            # Confidence can be normalized (e.g., max faces capped at 5)
            confidence = min(1.0, score / 5.0)
            reason = "Faces detected" if score > 0 else "No faces detected"
            return {"attention_score": score, "confidence": confidence, "reason": reason}

# -----------------------------
# Self-test
# -----------------------------
def webcam_test(duration_sec=10, display=False):
    detector = FaceDetector()
    detector.start_async()
    start_time = time.time()
    while time.time() - start_time < duration_sec:
        result = detector.get_latest_result()
        if display:
            print(result)
        time.sleep(0.5)
    detector.stop_async()
    print("Test finished.")

if __name__ == "__main__":
    webcam_test(duration_sec=15, display=True)
