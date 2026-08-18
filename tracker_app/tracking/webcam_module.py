"""Webcam pipeline: MediaPipe FaceMesh-based attention tracking (lazy-loaded)."""
import atexit
import datetime as _stdlib_dt
import cv2
import numpy as np
import time
import logging


def _utcnow():
    """Backward-compatible utcnow replacement (Python 3.12+ deprecation safe)."""
    return _stdlib_dt.datetime.now(_stdlib_dt.timezone.utc).replace(tzinfo=None)

logger = logging.getLogger("WebcamModule")

# ----------------------------
# Lazy MediaPipe initialisation
# ----------------------------
_face_mesh = None
_mp_face_mesh = None

def _get_face_mesh():
    """Lazily initialise MediaPipe FaceMesh on first use."""
    global _face_mesh, _mp_face_mesh
    if _face_mesh is None:
        try:
            import mediapipe as mp
            _mp_face_mesh = mp.solutions.face_mesh
            _face_mesh = _mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            logger.info("MediaPipe FaceMesh initialised successfully.")
        except Exception as e:
            logger.warning(f"MediaPipe FaceMesh init failed: {e}. Webcam attention disabled.")
            _face_mesh = None
    return _face_mesh

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
        logger.warning(f"Error calculating EAR: {e}")
        return 0.0

def calibrate_ear(duration_seconds=30):
    """Capture EAR samples over duration_seconds and compute per-user baselines.

    Returns a dict with personal_ear_low, personal_ear_high, mean_ear, std_ear,
    fallback flag, and calibrated_at timestamp. Falls back to defaults if the
    camera is unavailable or face detection fails for most samples.
    """
    from tracker_app.config import CALIBRATION_MIN_SAMPLES
    import datetime

    LEFT_EYE = [362, 385, 387, 263, 373, 380]
    RIGHT_EYE = [33, 160, 158, 133, 153, 144]
    face_mesh = _get_face_mesh()
    if face_mesh is None:
        return {"fallback": True, "reason": "mediapipe_unavailable"}

    ear_samples = []
    start = time.time()
    while time.time() - start < duration_seconds:
        frame = capture_frame()
        if frame is None:
            time.sleep(0.5)
            continue
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    lm = face_landmarks.landmark
                    left_ear = eye_aspect_ratio(lm, LEFT_EYE)
                    right_ear = eye_aspect_ratio(lm, RIGHT_EYE)
                    ear_samples.append((left_ear + right_ear) / 2.0)
        except Exception as exc:
            logger.warning(f'Calibration frame error: {exc}')
        time.sleep(0.1)

    if len(ear_samples) < CALIBRATION_MIN_SAMPLES:
        logger.warning("Calibration: only %d samples (need %d); using defaults",
                         len(ear_samples), CALIBRATION_MIN_SAMPLES)
        return {"fallback": True, "reason": "insufficient_samples",
                "samples": len(ear_samples)}

    mean_ear = float(np.mean(ear_samples))
    std_ear = float(np.std(ear_samples))
    personal_low = mean_ear - 1.5 * std_ear
    personal_high = mean_ear + 1.0 * std_ear

    if personal_low < 0.05 or personal_high > 0.50:
        logger.warning("Calibration: implausible range [%.3f, %.3f]; using defaults",
                         personal_low, personal_high)
        return {"fallback": True, "reason": "implausible_range",
                "mean_ear": mean_ear, "std_ear": std_ear}

    result = {
        "personal_ear_low": round(personal_low, 4),
        "personal_ear_high": round(personal_high, 4),
        "mean_ear": round(mean_ear, 4),
        "std_ear": round(std_ear, 4),
        "fallback": False,
        "calibrated_at": _utcnow().isoformat(),
    }
    logger.info("Calibration complete: low=%.3f high=%.3f mean=%.3f std=%.3f",
                personal_low, personal_high, mean_ear, std_ear)
    return result


def compute_attention_score(ear_values, ear_low=0.2, ear_high=0.35):
    """Compute attention score based on EAR history.

    When ear_low and ear_high are provided (from calibration), they
    replace the hardcoded 0.2/0.35 defaults.
    """
    if not ear_values:
        return 0.0

    avg_ear = np.mean(ear_values)
    ear_range = ear_high - ear_low

    if avg_ear < ear_low:
        return max(0.0, (avg_ear / max(ear_low, 0.01)) * 40.0)
    elif avg_ear > ear_high:
        return 100.0
    else:
        return 40.0 + ((avg_ear - ear_low) / max(ear_range, 0.01)) * 60.0

# ----------------------------
# Persistent camera handle
# ----------------------------
_cap = None  # cv2.VideoCapture opened once and reused (H-4)


def _get_cap():
    """Return the persistent camera handle, opening it on first use."""
    global _cap
    if _cap is None:
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                cap.release()
                return None
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            _cap = cap
        except Exception as e:
            logger.warning(f"Error opening camera: {e}")
            return None
    return _cap


def _release_cap():
    """Release the persistent camera handle (registered via atexit)."""
    global _cap
    if _cap is not None:
        try:
            _cap.release()
        except Exception:
            pass
        _cap = None


atexit.register(_release_cap)


# ----------------------------
# Capture a single frame
# ----------------------------
def capture_frame():
    cap = _get_cap()
    if cap is None:
        return None
    try:
        ret, frame = cap.read()
        if not ret or frame is None:
            # Camera dropped or returned no frame -- release so the next
            # cycle attempts a fresh open instead of reading a dead handle.
            _release_cap()
            return None
        return frame
    except Exception as e:
        logger.warning(f"Error capturing frame: {e}")
        return None

# ----------------------------
# Unified webcam pipeline
# ----------------------------
def webcam_pipeline(num_frames=3):
    """
    Process webcam frames to estimate attention
    """
    ear_values = []
    frames_processed = 0
    max_faces = 0
    
    # Indices for eyes in MediaPipe Face Mesh (approximate)
    # Left eye: 362, 385, 387, 263, 373, 380
    # Right eye: 33, 160, 158, 133, 153, 144
    LEFT_EYE = [362, 385, 387, 263, 373, 380] 
    RIGHT_EYE = [33, 160, 158, 133, 153, 144]

    face_mesh = _get_face_mesh()
    if face_mesh is None:
        # MediaPipe unavailable — return neutral score
        return {
            "attentiveness_score": 50.0,
            "face_count": 0,
            "frames_processed": 0,
            "status": "mediapipe_unavailable"
        }

    for _ in range(num_frames):
        frame = capture_frame()
        if frame is None:
            continue
            
        frames_processed += 1
        
        try:
            # Convert to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)
            faces_in_frame = len(results.multi_face_landmarks or [])
            if faces_in_frame > max_faces:
                max_faces = faces_in_frame
            
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    landmarks = face_landmarks.landmark
                    
                    left_ear = eye_aspect_ratio(landmarks, LEFT_EYE)
                    right_ear = eye_aspect_ratio(landmarks, RIGHT_EYE)
                    
                    avg_ear = (left_ear + right_ear) / 2.0
                    ear_values.append(avg_ear)
                    
        except Exception as e:
            logger.warning(f"Error in MediaPipe processing: {e}")
            continue
            
        # Small delay between frames
        time.sleep(0.1)

    attention_score = compute_attention_score(ear_values) if ear_values else 50.0
    
    # If no faces detected but frames processed, assume user is away
    if frames_processed > 0 and not ear_values:
        attention_score = 0.0

    return {
        "attentiveness_score": float(attention_score),
        "face_count": max_faces,
        "frames_processed": frames_processed,
        "status": "active" if ear_values else "no_face_detected"
    }

if __name__ == "__main__":
    print("Testing webcam pipeline...")
    result = webcam_pipeline()
    print(f"Status: {result['status']}")
    print(f"Attention Score: {result['attentiveness_score']:.1f}")
    print(f"Frames: {result['frames_processed']}")
