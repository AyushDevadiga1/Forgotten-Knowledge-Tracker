import sqlite3
import os
from datetime import datetime
from config import DB_PATH
import pytesseract
from PIL import Image

# ----------------------------
# Configuration
# ----------------------------
# Make sure Tesseract OCR is installed:
# Windows example: C:\Program Files\Tesseract-OCR\tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Test images folder
TEST_IMAGES_DIR = r"C:\Users\hp\Desktop\FKT\test_images"

# ----------------------------
# Connect to DB
# ----------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ----------------------------
# Function: Process Images & Insert OCR
# ----------------------------
def ocr_test_and_insert():
    for img_file in os.listdir(TEST_IMAGES_DIR):
        if img_file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
            img_path = os.path.join(TEST_IMAGES_DIR, img_file)
            print(f"\nProcessing image: {img_file}")

            # Perform OCR
            try:
                img = Image.open(img_path)
                ocr_text = pytesseract.image_to_string(img)
                ocr_text_clean = ocr_text.strip()
                print("Extracted OCR Text:\n", ocr_text_clean)

                # Insert into multi_modal_logs table
                cursor.execute("""
                    INSERT INTO multi_modal_logs
                    (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(),               # timestamp
                    img_file,                     # window_title
                    ocr_text_clean,               # ocr_keywords
                    "N/A",                        # audio_label
                    0.5,                          # attention_score
                    0.5,                          # interaction_rate
                    "N/A",                        # intent_label
                    0.0,                          # intent_confidence
                    0.3                           # memory_score
                ))
            except Exception as e:
                print(f"Error processing {img_file}: {e}")

    conn.commit()
    print("\nOCR test completed and inserted into DB.")
    conn.close()

# ----------------------------
# Run the Test
# ----------------------------
if __name__ == "__main__":
    ocr_test_and_insert()
