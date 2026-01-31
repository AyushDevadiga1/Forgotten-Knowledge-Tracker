# core/webcam_module.py
import cv2
import dlib
from imutils import face_utils
import numpy as np
from core.face_detection_module import FaceDetector

# Load face detector & landmarks predictor
detector = dlib.get_frontal_face_detector()
predictor_path = "core/shape_predictor_68_face_landmarks.dat"
try:
    predictor = dlib.shape_predictor(predictor_path)
except RuntimeError:
    print(f"dlib predictor not found at {predictor_path}. Webcam attention will be disabled.")
    predictor = None

face_detector = FaceDetector()  # For face presence

def eye_aspect_ratio(eye):
    """Compute EAR to detect blinks"""
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

def compute_attention_score(ear_values, face_presence=1.0):
    """Convert EAR & blink frequency + face presence into attentiveness score"""
    if len(ear_values) == 0:
        ear_score = 0.0
    else:
        avg_ear = np.mean(ear_values)
        ear_score = min(max((avg_ear - 0.18) * 500, 0), 100)
    # Weighted combination: 80% EAR, 20% face presence
    score = 0.8 * ear_score + 0.2 * face_presence * 100
    return score

def webcam_pipeline(num_frames=10):
    """
    Capture webcam frames and compute attention score.
    Returns 0 if no face detected or predictor not loaded.
    """
    if predictor is None and face_detector.detector is None:
        return {"attentiveness_score": 0}

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Webcam not available")
        return {"attentiveness_score": 0}

    ear_list = []
    face_presence_count = 0

    for _ in range(num_frames):
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        # Ensure proper 8-bit image
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Face detection
        faces, num_faces = face_detector.detect_faces(frame)
        face_presence_count += num_faces

        # EAR computation
        if predictor is not None:
            for face in faces:
                shape = predictor(gray, face)
                shape = face_utils.shape_to_np(shape)
                leftEye = shape[42:48]
                rightEye = shape[36:42]
                leftEAR = eye_aspect_ratio(leftEye)
                rightEAR = eye_aspect_ratio(rightEye)
                ear = (leftEAR + rightEAR) / 2.0
                ear_list.append(ear)

    cap.release()
    cv2.destroyAllWindows()

    # Compute final attentiveness score
    face_presence_score = face_presence_count / num_frames if num_frames else 0
    attention_score = compute_attention_score(ear_list, face_presence_score)

    return {"attentiveness_score": attention_score}


# -----------------------------
# Self-test / demo
# -----------------------------
if __name__ == "__main__":
    result = webcam_pipeline()
    print("Attention Score:", result['attentiveness_score'])
