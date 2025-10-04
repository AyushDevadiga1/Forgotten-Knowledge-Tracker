#core/__init__.py
import cv2
import dlib
from imutils import face_utils
import numpy as np

# Load face detector & landmarks predictor
detector = dlib.get_frontal_face_detector()
predictor_path = "core/shape_predictor_68_face_landmarks.dat"
try:
    predictor = dlib.shape_predictor(predictor_path)
except RuntimeError:
    print(f"dlib predictor not found at {predictor_path}. Webcam attention will be disabled.")
    predictor = None

def eye_aspect_ratio(eye):
    """Compute EAR to detect blinks"""
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

def compute_attention_score(ear_values):
    """Convert EAR & blink frequency into attentiveness score"""
    avg_ear = np.mean(ear_values)
    score = min(max((avg_ear - 0.18) * 500, 0), 100)  # Scale 0-100
    return score

def webcam_pipeline(num_frames=10):
    """
    Capture webcam frames and compute attention score.
    Returns 0 if no face detected or predictor not loaded.
    """
    if predictor is None:
        return {"attentiveness_score": 0}

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Webcam not available")
        return {"attentiveness_score": 0}

    ear_list = []

    for _ in range(num_frames):
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        # Ensure proper 8-bit image
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)

        if len(frame.shape) == 2:  # grayscale -> BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.shape[2] == 4:  # BGRA -> BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        try:
            faces = detector(gray)
        except Exception as e:
            print(f"dlib detection error: {e}")
            continue

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

    if ear_list:
        attention_score = compute_attention_score(ear_list)
    else:
        attention_score = 0  # no face detected

    return {"attentiveness_score": attention_score}

if __name__ == "__main__":
    result = webcam_pipeline()
    print("Attention Score:", result['attentiveness_score'])
