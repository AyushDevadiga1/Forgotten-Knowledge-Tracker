# core/webcam_module.py
import cv2
import numpy as np
import mediapipe as mp
import time

# ----------------------------
# MediaPipe Face Mesh Setup
# ----------------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# ----------------------------
# EAR & attention helpers
# ----------------------------
def eye_aspect_ratio(landmarks, eye_indices):
    """Calculate EAR using MediaPipe landmarks"""
    try:
        # Get coordinates
        p1 = np.array([landmarks[eye_indices[1]].x, landmarks[eye_indices[1]].y])
        p2 = np.array([landmarks[eye_indices[2]].x, landmarks[eye_indices[2]].y])
        p3 = np.array([landmarks[eye_indices[3]].x, landmarks[eye_indices[3]].y])
        p4 = np.array([landmarks[eye_indices[4]].x, landmarks[eye_indices[4]].y])
        p5 = np.array([landmarks[eye_indices[5]].x, landmarks[eye_indices[5]].y])
        p6 = np.array([landmarks[eye_indices[0]].x, landmarks[eye_indices[0]].y])

        # Calculate distances
        A = np.linalg.norm(p2 - p6)
        B = np.linalg.norm(p3 - p5)
        C = np.linalg.norm(p1 - p4)

        # Calculate EAR
        ear = (A + B) / (2.0 * C)
        return ear
    except Exception as e:
        print(f"Error calculating EAR: {e}")
        return 0.0

def compute_attention_score(ear_values):
    """Compute attention score based on EAR history"""
    if not ear_values:
        return 0.0
    
    avg_ear = np.mean(ear_values)
    
    # Heuristic: Normal EAR is around 0.25-0.35. Drowsy/closed is < 0.2
    # Attention score: 0 (asleep/closed) to 100 (fully alert)
    if avg_ear < 0.2:
        return max(0.0, (avg_ear / 0.2) * 40.0) # 0-40 range for low EAR
    elif avg_ear > 0.35:
        return 100.0 # Wide open eyes
    else:
        return 40.0 + ((avg_ear - 0.2) / 0.15) * 60.0 # 40-100 linear mapping

# ----------------------------
# Capture a single frame
# ----------------------------
def capture_frame():
    cap = None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        # Set resolution for faster processing
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        ret, frame = cap.read()
        if not ret or frame is None:
            return None
            
        return frame
    except Exception as e:
        print(f"Error capturing frame: {e}")
        return None
    finally:
        if cap is not None:
            cap.release()

# ----------------------------
# Unified webcam pipeline
# ----------------------------
def webcam_pipeline(num_frames=3):
    """
    Process webcam frames to estimate attention
    """
    ear_values = []
    frames_processed = 0
    
    # Indices for eyes in MediaPipe Face Mesh (approximate)
    # Left eye: 362, 385, 387, 263, 373, 380
    # Right eye: 33, 160, 158, 133, 153, 144
    LEFT_EYE = [362, 385, 387, 263, 373, 380] 
    RIGHT_EYE = [33, 160, 158, 133, 153, 144]

    for _ in range(num_frames):
        frame = capture_frame()
        if frame is None:
            continue
            
        frames_processed += 1
        
        try:
            # Convert to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)
            
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    landmarks = face_landmarks.landmark
                    
                    left_ear = eye_aspect_ratio(landmarks, LEFT_EYE)
                    right_ear = eye_aspect_ratio(landmarks, RIGHT_EYE)
                    
                    avg_ear = (left_ear + right_ear) / 2.0
                    ear_values.append(avg_ear)
                    
        except Exception as e:
            print(f"Error in MediaPipe processing: {e}")
            continue
            
        # Small delay between frames
        time.sleep(0.1)

    attention_score = compute_attention_score(ear_values) if ear_values else 50.0
    
    # If no faces detected but frames processed, assume user is away
    if frames_processed > 0 and not ear_values:
        attention_score = 0.0

    return {
        "attentiveness_score": float(attention_score),
        "face_count": 1 if ear_values else 0,
        "frames_processed": frames_processed,
        "status": "active" if ear_values else "no_face_detected"
    }

if __name__ == "__main__":
    print("Testing webcam pipeline...")
    result = webcam_pipeline()
    print(f"Status: {result['status']}")
    print(f"Attention Score: {result['attentiveness_score']:.1f}")
    print(f"Frames: {result['frames_processed']}")
