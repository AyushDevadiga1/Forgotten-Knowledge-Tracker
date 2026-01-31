# ==========================================================
# test_sensory_modules.py
# ==========================================================
"""
Comprehensive sensory test for FKT tracker:
- Screenshots + OCR
- Audio recording + classification
- Webcam + attention detection
- Keyboard & mouse interactions
"""

import time
import numpy as np

from core.ocr_module import ocr_pipeline
from core.audio_module import record_audio, extract_features as audio_extract_features
from core.webcam_module import webcam_pipeline
from core.face_detection_module import FaceDetector
from core.tracker import InteractionCounter, start_listeners

def test_webcam():
    print("\n[TEST] Webcam Pipeline")
    try:
        from core.webcam_module import webcam_pipeline
        result = webcam_pipeline(return_dict=True)
        frame = result.get("frame")
        faces = result.get("faces_detected", 0)
        attention = result.get("attentiveness", 0.0)
        if frame is not None:
            print(f"Faces detected: {faces}")
            print(f"Attentiveness score: {attention:.2f}")
        else:
            print("❌ No frame captured from webcam.")
    except Exception as e:
        print("Webcam test failed:", e)


def test_keyboard_mouse(duration=5):
    print("\n[TEST] Keyboard & Mouse Interaction")
    counter = InteractionCounter()
    kb_listener, ms_listener = start_listeners()
    print(f"Please type or click your mouse for {duration} seconds...")
    time.sleep(duration)
    kb_listener.stop()
    ms_listener.stop()
    print("Keyboard presses:", counter.keyboard)
    print("Mouse clicks:", counter.mouse)
    print("Total interactions:", counter.total())

if __name__ == "__main__":
    print("=== Sensory Module Test Started ===")
    test_ocr()
    test_audio()
    test_webcam()
    test_keyboard_mouse()
    print("\n=== Sensory Module Test Completed ===")
