import pytest
import os
from PIL import Image, ImageDraw
from core.ocr import OCRProcessor

class TestOCRProcessor:
    def setup_method(self):
        self.ocr = OCRProcessor()
        self.test_image_dir = "test_images"
        os.makedirs(self.test_image_dir, exist_ok=True)
        
        # Create a simple test image with text
        self.create_test_image()
    
    def teardown_method(self):
        # Clean up test files
        if os.path.exists(self.test_image_dir):
            for file in os.listdir(self.test_image_dir):
                os.remove(os.path.join(self.test_image_dir, file))
            os.rmdir(self.test_image_dir)
    
    def create_test_image(self):
        """Create a test image with some text"""
        # Create a white image
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw some text
        draw.text((50, 50), "Hello World!", fill='black')
        draw.text((50, 100), "OCR Test 123", fill='black')
        
        # Save the image
        test_image_path = os.path.join(self.test_image_dir, "test_ocr.png")
        img.save(test_image_path)
        self.test_image_path = test_image_path
    
    def test_initialization(self):
        """Test that OCR processor initializes correctly"""
        assert self.ocr is not None
        assert 'eng' in self.ocr.supported_languages
    
    def test_extract_text_from_image(self):
        """Test basic text extraction"""
        if os.path.exists(self.test_image_path):
            text = self.ocr.extract_text_from_image(self.test_image_path)
            assert text is not None
            assert isinstance(text, str)
            assert len(text) > 0
    
    def test_extract_text_with_confidence(self):
        """Test text extraction with confidence scores"""
        if os.path.exists(self.test_image_path):
            result = self.ocr.extract_text_with_confidence(self.test_image_path)
            assert result is not None
            assert 'text' in result
            assert 'confidence' in result
            assert 'word_count' in result
            assert result['confidence'] > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])