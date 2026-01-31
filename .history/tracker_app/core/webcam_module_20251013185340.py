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
        return max(0.0, ear)  # Ensure non-negative
    except Exception as e:
        print(f"Error computing EAR: {e}")
        return 0.0

def compute_attention_score(ear_values, face_count):
    """Convert EAR & face presence into attentiveness score"""
    if not ear_values:
        return 0.0 if face_count == 0 else 50.0  # No faces = 0, faces but no EAR data = 50
    
    try:
        avg_ear = np.mean(ear_values)
        
        # EAR typically ranges from 0.1 (closed) to 0.4 (open)
        # Map to 0-100 scale with reasonable bounds
        if avg_ear < 0.15:  # Likely closed/blinking
            base_score = 20.0
        elif avg_ear > 0.3:  # Very open/attentive
            base_score = 90.0
        else:  # Normal range
            base_score = 20.0 + (avg_ear - 0.15) * (90.0 - 20.0) / (0.3 - 0.15)
        
        # Boost score based on face presence consistency
        face_boost = min(10.0, face_count * 2.0)  # Small boost for multiple faces
        
        return min(100.0, base_score + face_boost)
        
    except Exception as e:
        print(f"Error computing attention score: {e}")
        return 50.0  # Default moderate attention

def capture_webcam_frame():
    """Capture a single webcam frame safely"""
    cap = None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Webcam not available")
            return None
            
        # Set reasonable resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        ret, frame = cap.read()
        if not ret or frame is None:
            return None
            
        return frame
        
    except Exception as e:
        print(f"Error capturing webcam frame: {e}")
        return None
    finally:
        if cap is not None:
            cap.release()

def webcam_pipeline(num_frames=5):
    """
    Capture webcam frames and compute attention score.
    Returns attention score with face count.
    """
    if predictor is None:
        # Fallback: basic face detection only
        try:
            frame = capture_webcam_frame()
            if frame is None:
                return {"attentiveness_score": 0, "face_count": 0}
                
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector(gray)
            face_count = len(faces)
            
            # Simple scoring based on face presence
            score = 0.0 if face_count == 0 else 60.0
            return {"attentiveness_score": score, "face_count": face_count}
            
        except Exception as e:
            print(f"Basic face detection failed: {e}")
            return {"attentiveness_score": 0, "face_count": 0}

    # Advanced pipeline with facial landmarks
    ear_list = []
    total_faces = 0
    frames_processed = 0

    for _ in range(num_frames):
        try:
            frame = capture_webcam_frame()
            if frame is None:
                continue

            # Ensure proper image format
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)

            # Handle different channel formats
            if len(frame.shape) == 2:  # grayscale
                gray = frame
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 4:  # BGRA
                gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            else:  # Assume BGR
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frame_bgr = frame

            # Detect faces
            faces = detector(gray)
            total_faces += len(faces)
            frames_processed += 1

            # Process each face for eye landmarks
            for face in faces:
                try:
                    shape = predictor(gray, face)
                    shape = face_utils.shape_to_np(shape)

                    # Extract eye coordinates
                    left_eye = shape[42:48]
                    right_eye = shape[36:42]
                    
                    left_ear = eye_aspect_ratio(left_eye)
                    right_ear = eye_aspect_ratio(right_eye)
                    
                    # Use average EAR of both eyes
                    ear = (left_ear + right_ear) / 2.0
                    ear_list.append(ear)
                    
                except Exception as e:
                    print(f"Error processing face landmarks: {e}")
                    continue

        except Exception as e:
            print(f"Error processing webcam frame: {e}")
            continue

    # Calculate final attention score
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