# core/webcam_module.py
import cv2
import dlib
from imutils import face_utils
import numpy as np

# Load face detector & landmarks predictor with error handling
detector = dlib.get_frontal_face_detector()
predictor_path = "core/shape_predictor_68_face_landmarks.dat"
predictor = None

try:
    predictor = dlib.shape_predictor(predictor_path)
    print("Facial landmark predictor loaded successfully.")
except Exception as e:
    print(f"dlib predictor not found at {predictor_path} or failed to load: {e}")
    print("Webcam attention will use basic face detection only.")

def eye_aspect_ratio(eye):
    """Compute EAR to detect blinks"""
    try:
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])
        C = np.linalg.norm(eye[0] - eye[3])
        ear = (A + B) / (2.0 * C)
        return max(0.0, ear)
    except Exception as e:
        print(f"Error computing EAR: {e}")
        return 0.0

def compute_attention_score(ear_values, face_count):
    """Convert EAR & face presence into attentiveness score"""
    if not ear_values:
        return 0.0 if face_count == 0 else 50.0
    try:
        avg_ear = np.mean(ear_values)
        if avg_ear < 0.15:
            base_score = 20.0
        elif avg_ear > 0.3:
            base_score = 90.0
        else:
            base_score = 20.0 + (avg_ear - 0.15) * (90.0 - 20.0) / (0.3 - 0.15)
        face_boost = min(10.0, face_count * 2.0)
        return min(100.0, base_score + face_boost)
    except Exception as e:
        print(f"Error computing attention score: {e}")
        return 50.0

def capture_webcam_frame():
    """Capture a single webcam frame and return as grayscale"""
    cap = None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Webcam not available")
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        ret, frame = cap.read()
        if not ret or frame is None:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    except Exception as e:
        print(f"Error capturing webcam frame: {e}")
        return None
    finally:
        if cap is not None:
            cap.release()

def webcam_pipeline(num_frames=5):
    """Capture webcam frames and compute attention score."""
    if predictor is None:
        try:
            frame = capture_webcam_frame()
            if frame is None:
                return {"attentiveness_score": 0, "face_count": 0}
            faces = detector(frame)
            score = 0.0 if len(faces) == 0 else 60.0
            return {"attentiveness_score": score, "face_count": len(faces)}
        except Exception as e:
            print(f"Basic face detection failed: {e}")
            return {"attentiveness_score": 0, "face_count": 0}

    ear_list = []
    total_faces = 0
    frames_processed = 0

    for _ in range(num_frames):
        try:
            gray = capture_webcam_frame()
            if gray is None:
                continue
            # Convert to BGR for dlib predictor if needed
            frame_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR) if len(gray.shape) == 2 else gray
            faces = detector(gray)
            total_faces += len(faces)
            frames_processed += 1
            for face in faces:
                try:
                    shape = predictor(gray, face)
                    shape = face_utils.shape_to_np(shape)
                    left_eye = shape[42:48]
                    right_eye = shape[36:42]
                    ear_list.append((eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2.0)
                except Exception as e:
                    print(f"Error processing face landmarks: {e}")
                    continue
        except Exception as e:
            print(f"Error processing webcam frame: {e}")
            continue

    avg_face_count = total_faces / max(1, frames_processed)
    attention_score = compute_attention_score(ear_list, avg_face_count)
    return {
        "attentiveness_score": attention_score,
        "face_count": int(avg_face_count),
        "frames_processed": frames_processed
    }

if __name__ == "__main__":
    result = webcam_pipeline()
    print(f"Attention Score: {result['attentiveness_score']:.1f}")
    print(f"Face Count: {result['face_count']}")
    print(f"Frames Processed: {result.get('frames_processed', 0)}")
