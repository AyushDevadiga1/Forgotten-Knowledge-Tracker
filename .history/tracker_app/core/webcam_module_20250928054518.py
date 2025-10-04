import cv2
import dlib
from imutils import face_utils
import numpy as np
import logging
from config import WEBCAM_ENABLED, USER_ALLOW_WEBCAM  # NEW

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NEW: Privacy-aware webcam initialization
def initialize_webcam_privacy_aware():
    """Initialize webcam only if enabled and permitted"""
    if not WEBCAM_ENABLED or not USER_ALLOW_WEBCAM:
        logger.info("Webcam disabled by user preference")
        return None
    
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            # Set lower resolution for privacy and performance
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            cap.set(cv2.CAP_PROP_FPS, 10)  # Lower frame rate
            logger.info("Webcam initialized with privacy settings")
            return cap
        else:
            logger.warning("Webcam not available")
            return None
    except Exception as e:
        logger.error(f"Webcam initialization error: {e}")
        return None

# NEW: Frame capture with privacy
def capture_frame_privacy_aware():
    """Capture single frame with privacy considerations"""
    if not WEBCAM_ENABLED or not USER_ALLOW_WEBCAM:
        return None
    
    cap = initialize_webcam_privacy_aware()
    if cap is None:
        return None
    
    try:
        ret, frame = cap.read()
        cap.release()
        
        if ret and frame is not None:
            # Apply privacy enhancements
            frame = apply_privacy_enhancements(frame)
            return frame
        else:
            return None
    except Exception as e:
        logger.error(f"Frame capture error: {e}")
        return None

# NEW: Privacy enhancements for frames
def apply_privacy_enhancements(frame):
    """Apply privacy enhancements to captured frame"""
    try:
        # Reduce image quality (blur slightly)
        frame = cv2.GaussianBlur(frame, (3, 3), 0)
        
        # Reduce color information (partial grayscale)
        h, w = frame.shape[:2]
        for i in range(0, h, 2):
            for j in range(0, w, 2):
                frame[i, j] = np.mean(frame[i, j])  # Partial grayscale
        
        return frame
    except Exception as e:
        logger.warning(f"Privacy enhancement error: {e}")
        return frame

# Load face detector & landmarks predictor - ORIGINAL
detector = dlib.get_frontal_face_detector()
predictor_path = "core/shape_predictor_68_face_landmarks.dat"
try:
    predictor = dlib.shape_predictor(predictor_path)
    logger.info("Face predictor loaded successfully")
except RuntimeError:
    logger.warning(f"dlib predictor not found at {predictor_path}. Webcam attention will be disabled.")
    predictor = None

# ORIGINAL FUNCTIONS - PRESERVED
def eye_aspect_ratio(eye):
    """ORIGINAL: Compute EAR to detect blinks"""
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

def compute_attention_score(ear_values):
    """ORIGINAL: Convert EAR & blink frequency into attentiveness score"""
    if not ear_values:
        return 0
    
    avg_ear = np.mean(ear_values)
    score = min(max((avg_ear - 0.18) * 500, 0), 100)  # Scale 0-100
    return score

# NEW: Enhanced attention scoring
def compute_enhanced_attention_score(faces, ear_values, head_pose=None):
    """
    Enhanced attention scoring with multiple factors
    - Face presence
    - Eye aspect ratio (blink detection)
    - Head pose estimation (basic)
    - Gaze direction (simplified)
    """
    if not WEBCAM_ENABLED or not USER_ALLOW_WEBCAM:
        return 0
    
    base_score = 0
    
    # Factor 1: Face presence (40% weight)
    face_score = min(len(faces) * 40, 40)  # Max 40 points for face presence
    base_score += face_score
    
    # Factor 2: Eye aspect ratio (30% weight)
    if ear_values:
        ear_score = compute_attention_score(ear_values) * 0.3  # 30 points max
        base_score += ear_score
    
    # Factor 3: Head stability (20% weight) - simplified
    if head_pose and len(head_pose) > 1:
        # Calculate head movement variance (lower movement = higher attention)
        movement_variance = np.var(head_pose)
        stability_score = max(0, 20 - (movement_variance * 10))  # Up to 20 points
        base_score += stability_score
    
    # Factor 4: Gaze direction (10% weight) - simplified
    gaze_score = 10  # Assume forward gaze by default
    base_score += gaze_score
    
    return min(100, base_score)

# NEW: Basic head pose estimation
def estimate_head_pose(face_landmarks):
    """Simple head pose estimation using facial landmarks"""
    try:
        if face_landmarks is None or len(face_landmarks) < 68:
            return None
        
        # Use nose and eye positions for simple pose estimation
        nose_tip = face_landmarks[30]  # Nose tip
        left_eye_center = np.mean(face_landmarks[36:42], axis=0)
        right_eye_center = np.mean(face_landmarks[42:48], axis=0)
        
        # Calculate simple head orientation
        eye_center = (left_eye_center + right_eye_center) / 2
        horizontal_offset = nose_tip[0] - eye_center[0]
        vertical_offset = nose_tip[1] - eye_center[1]
        
        return [horizontal_offset, vertical_offset]
    except Exception as e:
        logger.debug(f"Head pose estimation error: {e}")
        return None

# NEW: Enhanced webcam pipeline
def enhanced_webcam_pipeline(num_frames=5):
    """
    Enhanced webcam pipeline with privacy controls and better attention scoring
    """
    if not WEBCAM_ENABLED or not USER_ALLOW_WEBCAM:
        return {"attentiveness_score": 0, "faces_detected": 0, "privacy_enabled": True}
    
    if predictor is None:
        return {"attentiveness_score": 0, "faces_detected": 0, "predictor_available": False}

    ear_list = []
    head_poses = []
    face_count = 0

    for _ in range(num_frames):
        frame = capture_frame_privacy_aware()
        if frame is None:
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
            face_count = max(face_count, len(faces))
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            continue

        for face in faces:
            try:
                shape = predictor(gray, face)
                shape = face_utils.shape_to_np(shape)

                leftEye = shape[42:48]
                rightEye = shape[36:42]
                leftEAR = eye_aspect_ratio(leftEye)
                rightEAR = eye_aspect_ratio(rightEye)
                ear = (leftEAR + rightEAR) / 2.0
                ear_list.append(ear)
                
                # Estimate head pose
                head_pose = estimate_head_pose(shape)
                if head_pose:
                    head_poses.append(head_pose)
                    
            except Exception as e:
                logger.debug(f"Landmark detection error: {e}")
                continue

    # Calculate enhanced attention score
    attention_score = compute_enhanced_attention_score(
        faces=list(range(face_count)),  # Simulate face objects
        ear_values=ear_list,
        head_pose=head_poses
    )

    return {
        "attentiveness_score": attention_score,
        "faces_detected": face_count,
        "ear_samples": len(ear_list),
        "head_pose_samples": len(head_poses),
        "privacy_enabled": True
    }

# ORIGINAL FUNCTION - PRESERVED
def webcam_pipeline(num_frames=10):
    """
    ORIGINAL: Capture webcam frames and compute attention score.
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

# NEW: Attention pattern analysis
def analyze_attention_pattern(attention_scores, time_window=10):
    """
    Analyze attention patterns over time to detect focus trends
    """
    if not attention_scores or len(attention_scores) < time_window:
        return {"trend": "insufficient_data", "stability": 0, "average_attention": 0}
    
    recent_scores = attention_scores[-time_window:]
    
    # Calculate trend
    if len(recent_scores) >= 2:
        trend = "stable"
        if recent_scores[-1] > np.mean(recent_scores[:-1]) + 10:
            trend = "improving"
        elif recent_scores[-1] < np.mean(recent_scores[:-1]) - 10:
            trend = "declining"
    else:
        trend = "unknown"
    
    # Calculate stability (inverse of variance)
    stability = max(0, 1 - (np.var(recent_scores) / 1000))
    average_attention = np.mean(recent_scores)
    
    return {
        "trend": trend,
        "stability": stability,
        "average_attention": average_attention,
        "samples_analyzed": len(recent_scores)
    }

if __name__ == "__main__":
    # Test both pipelines
    print("Testing original webcam pipeline:")
    result = webcam_pipeline(num_frames=3)
    print("Original - Attention Score:", result['attentiveness_score'])
    
    print("\nTesting enhanced webcam pipeline:")
    result_enhanced = enhanced_webcam_pipeline(num_frames=3)
    print("Enhanced - Attention Score:", result_enhanced['attentiveness_score'])
    print("Enhanced - Faces Detected:", result_enhanced['faces_detected'])
    print("Enhanced - Privacy Enabled:", result_enhanced['privacy_enabled'])
    
    # Test attention pattern analysis
    test_scores = [65, 70, 68, 72, 75, 80, 78, 82, 85, 83]
    pattern_analysis = analyze_attention_pattern(test_scores)
    print("Attention Pattern Analysis:", pattern_analysis)