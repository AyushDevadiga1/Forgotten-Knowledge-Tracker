# core/face_detection_module.py
import cv2
import dlib
import time
import num

class FaceDetector:
    def __init__(self):
        try:
            self.detector = dlib.get_frontal_face_detector()
            print("Face detector loaded successfully.")
        except Exception as e:
            self.detector = None
            print(f"Error loading face detector: {e}")

    def detect_faces(self, frame):
        """
        Detect faces in a given RGB frame.
        Returns list of dlib rectangles and number of faces.
        """
        if frame is None or self.detector is None:
            return [], 0
        
        # Ensure frame is proper type and format
        if not isinstance(frame, (np.ndarray,)):
            return [], 0
            
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
            
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            except:
                rgb_frame = frame
        else:
            rgb_frame = frame
            
        try:
            faces = self.detector(rgb_frame, 0)
            return faces, len(faces)
        except Exception as e:
            print(f"dlib detection error: {e}")
            return [], 0

def webcam_test(duration_sec=10, display=True):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return 0.0
        
    detector = FaceDetector()
    start_time = time.time()
    frame_count = 0
    face_frames = 0

    while time.time() - start_time < duration_sec:
        ret, frame = cap.read()
        if not ret:
            continue
            
        frame_count += 1
        faces, num_faces = detector.detect_faces(frame)
        if num_faces > 0:
            face_frames += 1

        if display:
            for face in faces:
                x, y, w, h = face.left(), face.top(), face.width(), face.height()
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.imshow("Webcam Face Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    presence_score = face_frames / frame_count if frame_count else 0
    print(f"Test finished. Face presence score: {presence_score:.2f}")
    return presence_score

if __name__ == "__main__":
    webcam_test(duration_sec=15)