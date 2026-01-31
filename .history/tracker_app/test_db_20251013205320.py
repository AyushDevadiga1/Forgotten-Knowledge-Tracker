import cv2
from PIL import Image
import pytesseract
import numpy as np

# ----------------------------
# Configure Tesseract OCR
# ----------------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ----------------------------
# Capture Current Webcam Frame
# ----------------------------
def capture_and_ocr():
    cap = cv2.VideoCapture(0)  # 0 = default webcam
    if not cap.isOpened():
        print("Cannot open webcam")
        return

    print("Press 'q' to quit after capturing a frame")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Show frame
        cv2.imshow("Webcam - Press 'c' to capture", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("c"):  # capture current frame
            # Convert BGR (OpenCV) -> RGB (PIL)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)

            # Run OCR
            ocr_text = pytesseract.image_to_string(pil_img).strip()
            print("\n--- OCR Result ---")
            print(ocr_text if ocr_text else "[No text detected]")
            print("------------------\n")

        elif key == ord("q"):  # quit
            break

    cap.release()
    cv2.destroyAllWindows()

# ----------------------------
# Run the Test
# ----------------------------
if __name__ == "__main__":
    capture_and_ocr()

