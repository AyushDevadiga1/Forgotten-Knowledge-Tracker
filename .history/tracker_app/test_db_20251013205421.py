import cv2
from PIL import Image
import pytesseract

# ----------------------------
# Configure Tesseract OCR
# ----------------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # adjust if needed

# ----------------------------
# Capture current webcam frame
# ----------------------------
cap = cv2.VideoCapture(0)  # 0 = default webcam
if not cap.isOpened():
    print("Cannot open webcam")
    exit()

print("Press 'c' to capture a frame and run OCR, 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    cv2.imshow("Webcam Live", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord('c'):
        # Convert frame to RGB for OCR
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)

        # Run OCR
        text = pytesseract.image_to_string(pil_img)
        print("\n--- OCR Result ---")
        print(text.strip() if text.strip() else "[No text detected]")
        print("------------------\n")

    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
