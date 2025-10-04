# core/face_detection_module.py - ENHANCED VERSION
import cv2
import dlib
import time
import logging
import numpy as np
from config import WEBCAM_ENABLED, USER_ALLOW_WEBCAM  # NEW

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FaceDetector:
    def __init__(self, enable_landmarks=False):
        """
        Enhanced face detector with privacy controls
        """
        self.enable_landmarks = enable_landmarks
        self.detector = None
        self.predictor = None
        self.initialized = False
        
        if not WEBCAM_ENABLED or not USER_ALLOW_WEBCAM:
            logger.info("Face detection disabled by user preference")
            return
            
        self.initialize_detector()
    
    def initialize_detector(self):
        """Initialize face detection components with error handling"""
        try:
            self.detector = dlib.get_frontal_face_detector()
            logger.info("Face detector loaded successfully.")
            
            if self.enable_landmarks:
                predictor_path = "core/shape_predictor_68_face_landmarks.dat"
                try:
                    self.predictor = dlib.shape_predictor(predictor_path)
                    logger.info("Face landmark predictor loaded successfully.")
                except Exception as e:
                    logger.warning(f"Landmark predictor not available: {e}")
                    self.predictor = None
            
            self.initialized = True
        except Exception as e:
            logger.error(f"Error loading face detector: {e}")
            self.initialized = False

    def detect_faces(self, frame):
        """
        Enhanced face detection with privacy awareness and better error handling
        """
        if not WEBCAM_ENABLED or not USER_ALLOW_WEBCAM:
            return [], 0, {"privacy_enabled": True}
        
        if frame is None or self.detector is None or not self.initialized:
            return [], 0, {"error": "detector_not_ready"}
        
        # Ensure frame is proper format
        frame = self.validate_frame(frame)
        if frame is None:
            return [], 0, {"error": "invalid_frame"}
        
        try:
            # Convert to RGB for dlib
            if len(frame.shape) == 3:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            
            # Detect faces
            faces = self.detector(rgb_frame, 1)  # Upsample once for better detection
            
            # Extract face details
            face_details = []
            for face in faces:
                face_info = {
                    'bbox': (face.left(), face.top(), face.width(), face.height()),
                    'confidence': face.confidence if hasattr(face, 'confidence') else 1.0,
                    'landmarks': None
                }
                
                # Extract landmarks if enabled
                if self.predictor and self.enable_landmarks:
                    try:
                        landmarks = self.predictor(rgb_frame, face)
                        face_info['landmarks'] = [(p.x, p.y) for p in landmarks.parts()]
                    except Exception as e:
                        logger.debug(f"Landmark extraction error: {e}")
                
                face_details.append(face_info)
            
            detection_metadata = {
                'frame_shape': frame.shape,
                'detection_time': time.time(),
                'privacy_enabled': False,
                'landmarks_available': self.predictor is not None
            }
            
            return face_details, len(faces), detection_metadata
            
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return [], 0, {"error": str(e)}

    def validate_frame(self, frame):
        """Validate and preprocess frame for face detection"""
        if frame is None:
            return None
        
        # Ensure correct data type
        if frame.dtype != np.uint8:
            try:
                frame = frame.astype(np.uint8)
            except:
                return None
        
        # Ensure correct shape
        if len(frame.shape) not in [2, 3]:
            return None
        
        # Ensure reasonable size
        if frame.shape[0] < 50 or frame.shape[1] < 50:
            return None
        
        return frame

    def estimate_attention_from_faces(self, face_details, frame_shape):
        """
        Estimate attention level based on face detection results
        """
        if not face_details:
            return 0, {"reason": "no_faces"}
        
        attention_score = 0
        attention_factors = []
        
        for face in face_details:
            bbox = face['bbox']
            face_center_x = bbox[0] + bbox[2] / 2
            face_center_y = bbox[1] + bbox[3] / 2
            
            # Factor 1: Face size relative to frame (larger faces = more attention)
            frame_area = frame_shape[0] * frame_shape[1]
            face_area = bbox[2] * bbox[3]
            size_factor = min(face_area / (frame_area * 0.1), 1.0)  # Normalize
            
            # Factor 2: Face position (center = more attention)
            center_x = frame_shape[1] / 2
            center_y = frame_shape[0] / 2
            distance_to_center = np.sqrt((face_center_x - center_x)**2 + (face_center_y - center_y)**2)
            max_distance = np.sqrt(center_x**2 + center_y**2)
            position_factor = 1.0 - (distance_to_center / max_distance)
            
            # Factor 3: Face confidence
            confidence_factor = face.get('confidence', 0.5)
            
            # Combined face attention
            face_attention = (size_factor * 0.4 + position_factor * 0.4 + confidence_factor * 0.2) * 100
            attention_factors.append(face_attention)
        
        # Use maximum attention from any face
        if attention_factors:
            attention_score = max(attention_factors)
        
        attention_metadata = {
            'faces_detected': len(face_details),
            'max_attention': attention_score,
            'average_attention': np.mean(attention_factors) if attention_factors else 0,
            'attention_factors': attention_factors
        }
        
        return min(100, attention_score), attention_metadata

# NEW: Privacy-aware webcam test
def webcam_test_enhanced(duration_sec=10, display=True, privacy_mode=True):
    """
    Enhanced webcam test with privacy controls
    """
    if not WEBCAM_ENABLED or not USER_ALLOW_WEBCAM:
        print("Webcam testing disabled by user preference")
        return 0
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Webcam not available")
        return 0
    
    detector = FaceDetector(enable_landmarks=True)
    start_time = time.time()
    frame_count = 0
    face_frames = 0
    attention_scores = []
    
    # Set lower resolution for privacy
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    
    print(f"Starting enhanced webcam test for {duration_sec} seconds...")
    print("Press 'q' to exit early")
    
    while time.time() - start_time < duration_sec:
        ret, frame = cap.read()
        if not ret:
            continue
        
        frame_count += 1
        
        # Apply privacy enhancements if enabled
        if privacy_mode:
            frame = apply_privacy_filter(frame)
        
        # Detect faces
        faces, num_faces, metadata = detector.detect_faces(frame)
        
        if num_faces > 0:
            face_frames += 1
            
            # Estimate attention
            attention_score, attention_meta = detector.estimate_attention_from_faces(faces, frame.shape)
            attention_scores.append(attention_score)
        
        if display:
            # Draw detection results
            display_frame = frame.copy()
            
            for face in faces:
                bbox = face['bbox']
                cv2.rectangle(display_frame, 
                            (bbox[0], bbox[1]), 
                            (bbox[0] + bbox[2], bbox[1] + bbox[3]), 
                            (0, 255, 0), 2)
                
                # Draw landmarks if available
                if face['landmarks']:
                    for landmark in face['landmarks']:
                        cv2.circle(display_frame, landmark, 2, (0, 0, 255), -1)
            
            # Display attention score
            current_attention = attention_scores[-1] if attention_scores else 0
            cv2.putText(display_frame, f"Attention: {current_attention:.1f}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow("Enhanced Face Detection Test", display_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Calculate results
    presence_score = face_frames / frame_count if frame_count else 0
    avg_attention = np.mean(attention_scores) if attention_scores else 0
    
    print(f"\nTest completed:")
    print(f"  Frames processed: {frame_count}")
    print(f"  Face detection rate: {presence_score:.2%}")
    print(f"  Average attention score: {avg_attention:.1f}")
    print(f"  Privacy mode: {'Enabled' if privacy_mode else 'Disabled'}")
    
    return avg_attention

# NEW: Privacy filter for webcam frames
def apply_privacy_filter(frame):
    """
    Apply privacy-enhancing filters to webcam frames
    """
    try:
        # Mild Gaussian blur
        frame = cv2.GaussianBlur(frame, (5, 5), 0)
        
        # Reduce color saturation
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = hsv[:, :, 1] * 0.7  # Reduce saturation
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        # Add slight noise for privacy
        noise = np.random.normal(0, 3, frame.shape).astype(np.uint8)
        frame = cv2.add(frame, noise)
        
        return frame
    except Exception as e:
        logger.warning(f"Privacy filter error: {e}")
        return frame

# ORIGINAL FUNCTION - PRESERVED
def webcam_test(duration_sec=10, display=True):
    """
    ORIGINAL: Basic webcam test function
    """
    cap = cv2.VideoCapture(0)
    detector = FaceDetector()
    start_time = time.time()
    frame_count = 0
    face_frames = 0

    while time.time() - start_time < duration_sec:
        ret, frame = cap.read()
        if not ret:
            continue
        frame_count += 1
        faces, num_faces, _ = detector.detect_faces(frame)
        if num_faces > 0:
            face_frames += 1

        if display:
            for face in faces:
                bbox = face['bbox']
                x, y, w, h = bbox
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.imshow("Webcam Face Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    presence_score = face_frames / frame_count if frame_count else 0
    print(f"Original test - Face presence score: {presence_score:.2f}")
    return presence_score

if __name__ == "__main__":
    print("Testing original face detection:")
    original_score = webcam_test(duration_sec=5, display=False)
    
    print("\nTesting enhanced face detection:")
    enhanced_score = webcam_test_enhanced(duration_sec=5, display=True, privacy_mode=True)
    
    print(f"\nComparison:")
    print(f"  Original presence score: {original_score:.2f}")
    print(f"  Enhanced attention score: {enhanced_score:.1f}")