import pytesseract
from PIL import ImageGrab

# ----------------------------
# Configure Tesseract OCR
# ----------------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # adjust if needed

# ----------------------------
# Capture current screen
# ----------------------------
print("Capturing the screen...")
screenshot = ImageGrab.grab()  # grabs the whole screen

# ----------------------------
# Run OCR on the screenshot
# ----------------------------
text = pytesseract.image_to_string(screenshot)

print("\n--- OCR Result ---")
print(text.strip() if text.strip() else "[No text detected]")
print("------------------")
