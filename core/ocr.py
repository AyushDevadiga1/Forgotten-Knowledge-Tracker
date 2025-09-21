# Phase 2: OCR
import pytesseract
from PIL import Image
import sqlite3
from config import DB_PATH

# Optional: set Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def run_ocr(image_path, session_id=None):
    text = pytesseract.image_to_string(Image.open(image_path))
    
    # Simple keyword extraction: split words, remove short words
    keywords = [w for w in text.split() if len(w) > 3]
    keywords_str = ','.join(keywords[:20])  # take top 20
    
    # Save to DB if session_id provided
    if session_id:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ocr_logs (session_id, raw_text, keywords) VALUES (?, ?, ?)",
            (session_id, text, keywords_str)
        )
        conn.commit()
        conn.close()
    
    return text, keywords
