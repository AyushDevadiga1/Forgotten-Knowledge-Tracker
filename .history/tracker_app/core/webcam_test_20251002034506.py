#core/__init__.py
import cv2
import dlib
import numpy as np

cap = cv2.VideoCapture(0)
detector = dlib.get_frontal_face_detector()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Ensure frame is uint8 and contiguous
    frame = np.ascontiguousarray(frame, dtype=np.uint8)

    # Convert BGR -> RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb_frame = np.ascontiguousarray(rgb_frame, dtype=np.uint8)

    print(f"Frame dtype={frame.dtype}, shape={frame.shape}")
    print(f"RGB dtype={rgb_frame.dtype}, shape={rgb_frame.shape}")

    try:
        faces = detector(rgb_frame)
        print(f"Faces detected: {len(faces)}")
    except Exception as e:
        print(f"dlib detection error: {e}")

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
