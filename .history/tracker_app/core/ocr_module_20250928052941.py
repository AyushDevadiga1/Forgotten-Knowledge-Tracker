import cv2
import numpy as np
import pytesseract
from mss import mss
from config import TESSERACT_PATH
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
import re  # NEW: For PII redaction

# Set tesseract executable path - ORIGINAL
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Initialize models - ORIGINAL
kw_model = KeyBERT()
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# NEW: PII Redaction functions
def redact_pii(text):
    """Redact personally identifiable information from text"""
    if not text:
        return text
    
    # Redact email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
    
    # Redact phone numbers
    text = re.sub(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE_REDACTED]', text)
    
    # Redact credit card numbers
    text = re.sub(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[CARD_REDACTED]', text)
    
    # Redact social security numbers (US)
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
    
    return text

def blur_faces(image):
    """Blur faces in the image using OpenCV"""
    try:
        # Load face detection classifier
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        if face_cascade.empty():
            print("Face cascade classifier not found. Skipping face blurring.")
            return image
            
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        # Blur each face
        for (x, y, w, h) in faces:
            face_region = image[y:y+h, x:x+w]
            # Use Gaussian blur for face region
            blurred_face = cv2.GaussianBlur(face_region, (99, 99), 30)
            image[y:y+h, x:x+w] = blurred_face
            
        return image
    except Exception as e:
        print(f"Face blurring error: {e}")
        return image

# NEW: Targeted screenshot capture
def targeted_screenshot():
    """Capture screenshot only for study-related apps"""
    from core.tracker import get_active_window  # Import here to avoid circular imports
    
    window_title, app_type, _ = get_active_window()
    
    # Only capture if active window is study-related
    if app_type in ["browser", "document", "study"]:
        return capture_screenshot()
    else:
        print(f"Skipping OCR for non-study app: {app_type} - {window_title}")
        return None

# ORIGINAL FUNCTIONS - PRESERVED
def capture_screenshot():
    """ORIGINAL: Capture full screen"""
    try:
        with mss() as sct:
            screenshot = sct.grab(sct.monitors[1])
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None

def preprocess_image(img):
    """ORIGINAL: Grayscale + contrast for OCR"""
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    return gray

def extract_text(img):
    """ORIGINAL: Run OCR on preprocessed image"""
    if img is None:
        return ""
    text = pytesseract.image_to_string(img)
    return text

def extract_keywords(text, top_n=5):
    """ORIGINAL: Extract top study keywords using KeyBERT"""
    if not text.strip():
        return []
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2), stop_words='english', top_n=top_n)
    return [kw[0] for kw in keywords]

def get_embeddings(text):
    """ORIGINAL: Get sentence embeddings"""
    if not text.strip():
        return np.zeros(384)  # Return zero vector for empty text
    return embedding_model.encode([text])[0]

# NEW: Enhanced OCR pipeline with PII redaction
def enhanced_ocr_pipeline():
    """Enhanced OCR with PII redaction and targeted capture"""
    from config import OCR_ENABLED, BLUR_FACES, REDACT_EMAILS
    
    if not OCR_ENABLED:
        return {"raw_text": "", "keywords": [], "embedding": np.zeros(384), "confidence": 0.0}
    
    img = targeted_screenshot()
    if img is None:
        return {"raw_text": "", "keywords": [], "embedding": np.zeros(384), "confidence": 0.0}
    
    # Apply face blurring if enabled
    if BLUR_FACES:
        img = blur_faces(img)
    
    processed = preprocess_image(img)
    text = extract_text(processed)
    
    # Apply PII redaction
    if REDACT_EMAILS:
        text = redact_pii(text)
    
    keywords = extract_keywords(text)
    embedding = get_embeddings(text)
    
    # Calculate confidence based on text length and keyword quality
    confidence = min(len(text) / 1000, 1.0)  # Simple confidence metric
    
    return {
        "raw_text": text,
        "keywords": keywords,
        "embedding": embedding,
        "confidence": confidence
    }

# ORIGINAL FUNCTION - PRESERVED
def ocr_pipeline():
    """ORIGINAL: OCR pipeline without enhancements"""
    img = capture_screenshot()
    processed = preprocess_image(img)
    text = extract_text(processed)
    keywords = extract_keywords(text)
    embedding = get_embeddings(text)
    return {
        "raw_text": text,
        "keywords": keywords,
        "embedding": embedding
    }

if __name__ == "__main__":
    # Test both pipelines
    print("Testing original OCR pipeline:")
    result = ocr_pipeline()
    print("Keywords:", result['keywords'][:3])
    print("Text snippet:", result['raw_text'][:200])
    
    print("\nTesting enhanced OCR pipeline:")
    result_enhanced = enhanced_ocr_pipeline()
    print("Keywords:", result_enhanced['keywords'][:3])
    print("Text snippet:", result_enhanced['raw_text'][:200])
    print("Confidence:", result_enhanced['confidence'])