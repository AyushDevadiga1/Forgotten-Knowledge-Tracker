import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import logging
import os
import re
import platform

# Configure Tesseract path based on operating system
def setup_tesseract():
    """Configure Tesseract path based on operating system"""
    system = platform.system()
    
    if system == "Windows":
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            os.environ.get('TESSERACT_CMD', '')  # Check environment variable
        ]
    elif system == "Darwin":  # macOS
        possible_paths = [
            '/usr/local/bin/tesseract',
            '/opt/homebrew/bin/tesseract',
            '/usr/bin/tesseract'
        ]
    else:  # Linux
        possible_paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract'
        ]
    
    # Try to find Tesseract
    for path in possible_paths:
        if path and os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return path
    
    # Last resort: try to find in PATH
    try:
        which_path = os.popen('which tesseract').read().strip()
        if which_path:
            pytesseract.pytesseract.tesseract_cmd = which_path
            return which_path
    except:
        pass
    
    raise Exception("Tesseract not found. Please install Tesseract OCR and ensure it's in your PATH or set TESSERACT_PATH environment variable.")

# Initialize Tesseract
try:
    tesseract_path = setup_tesseract()
    logger = logging.getLogger(__name__)
    logger.info(f"Tesseract initialized at: {tesseract_path}")
except Exception as e:
    # Fallback: try common Windows path
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    logger = logging.getLogger(__name__)
    logger.warning(f"Tesseract setup failed, using default path: {e}")

class OCRProcessor:
    def __init__(self):
        """Initialize OCR processor"""
        # Verify tesseract is working
        try:
            available_languages = pytesseract.get_languages()
            logger.info(f"OCR Processor initialized. Supported languages: {available_languages}")
        except Exception as e:
            logger.error(f"OCR initialization error: {e}")
    
    def preprocess_image(self, image):
        """Preprocess image to improve OCR accuracy"""
        try:
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Apply slight blur to smooth text
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            return image
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return image
    
    def extract_text_from_image(self, image_path, preprocess=True):
        """Extract text from an image using OCR"""
        try:
            # Open image
            image = Image.open(image_path)
            
            # Preprocess if requested
            if preprocess:
                image = self.preprocess_image(image)
            
            # Extract text
            text = pytesseract.image_to_string(image, lang='eng')
            
            # Clean up text
            text = self._clean_text(text)
            
            # Calculate basic metrics
            word_count = len(text.split()) if text.strip() else 0
            char_count = len(text)
            
            result = {
                'text': text,
                'word_count': word_count,
                'char_count': char_count,
                'confidence': 85.0  # Default confidence
            }
            
            logger.info(f"OCR completed for {image_path}: {char_count} characters")
            return result
            
        except Exception as e:
            logger.error(f"OCR extraction error for {image_path}: {e}")
            return {
                'text': '',
                'word_count': 0,
                'char_count': 0,
                'confidence': 0.0
            }
    
    def extract_text_with_confidence(self, image_path, preprocess=True):
        """Extract text with confidence scores"""
        try:
            # Open image
            image = Image.open(image_path)
            
            # Preprocess if requested
            if preprocess:
                image = self.preprocess_image(image)
            
            # Get detailed OCR data
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Extract text and calculate average confidence
            words = []
            confidences = []
            
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                confidence = int(ocr_data['conf'][i])
                
                if text and confidence > 0:  # Filter out empty strings and low confidence
                    words.append(text)
                    confidences.append(confidence)
            
            # Combine words and calculate metrics
            extracted_text = ' '.join(words)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            result = {
                'text': extracted_text,
                'word_count': len(words),
                'char_count': len(extracted_text),
                'confidence': round(avg_confidence, 2)
            }
            
            logger.info(f"Confidence-based OCR: {len(words)} words, {avg_confidence:.2f}% confidence")
            return result
            
        except Exception as e:
            logger.error(f"Confidence OCR error for {image_path}: {e}")
            return self.extract_text_from_image(image_path, preprocess)
    
    def _clean_text(self, text):
        """Clean extracted text"""
        if not text:
            return ""
        
        # Remove multiple whitespace characters
        text = re.sub(r'\s+', ' ', text)
        
        # Remove non-printable characters except common ones
        text = re.sub(r'[^\x20-\x7E\n\r\t]', '', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def get_supported_languages(self):
        """Get list of supported OCR languages"""
        try:
            return pytesseract.get_languages()
        except Exception as e:
            logger.error(f"Error getting supported languages: {e}")
            return ['eng']