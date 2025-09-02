#!/usr/bin/env python3
"""
Complete test of the screenshot + OCR workflow
"""
import logging
import os
import time
from PIL import Image, ImageDraw, ImageFont
from core.screenshot import ScreenshotCapturer
from core.ocr import OCRProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def create_test_image():
    """Create a test image with text for OCR testing"""
    test_dir = "test_ocr_images"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create a simple image with text
    img = Image.new('RGB', (800, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # Use default font (size may vary)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    # Draw test text
    text_lines = [
        "Forgotten Knowledge Tracker",
        "OCR Test - Phase 2 Implementation",
        "Hello World! 123 ABC",
        "Testing text extraction capabilities",
        "This should be readable by Tesseract OCR"
    ]
    
    y_position = 50
    for line in text_lines:
        draw.text((50, y_position), line, fill='black', font=font)
        y_position += 60
    
    # Save the image
    test_image_path = os.path.join(test_dir, "ocr_test_image.png")
    img.save(test_image_path)
    print(f"✅ Created test image: {test_image_path}")
    
    return test_image_path

def test_screenshot_capture():
    """Test screenshot functionality"""
    print("\n" + "="*50)
    print("Testing Screenshot Capture...")
    
    capturer = ScreenshotCapturer(output_dir="test_screenshots")
    
    # Capture a screenshot
    result = capturer.capture_screenshot("test_screenshot.png")
    
    if result:
        print(f"✅ Screenshot captured: {result['path']}")
        print(f"   Size: {result['dimensions']}, File size: {result['size']} bytes")
        return result['path']
    else:
        print("❌ Screenshot capture failed")
        return None

def test_ocr_processing(image_path):
    """Test OCR functionality"""
    print("\n" + "="*50)
    print("Testing OCR Processing...")
    
    ocr = OCRProcessor()
    
    # Test basic text extraction
    print("Testing basic text extraction...")
    text = ocr.extract_text_from_image(image_path)
    
    if text:
        print("✅ OCR Text extracted successfully!")
        print(f"Text length: {len(text)} characters")
        print("\nExtracted text preview:")
        print("-" * 40)
        print(text[:200] + "..." if len(text) > 200 else text)
        print("-" * 40)
    else:
        print("❌ OCR text extraction failed")
        return False
    
    # Test confidence-based extraction
    print("\nTesting confidence-based extraction...")
    result = ocr.extract_text_with_confidence(image_path)
    
    if result:
        print("✅ Confidence-based OCR successful!")
        print(f"Word count: {result['word_count']}")
        print(f"Confidence: {result['confidence']}%")
        print(f"Character count: {result['character_count']}")
        return True
    else:
        print("❌ Confidence-based OCR failed")
        return False

def main():
    print("🔍 Testing Complete Screenshot + OCR Workflow")
    print("="*60)
    
    # Create test image first (more reliable than screenshot for testing)
    test_image_path = create_test_image()
    
    # Test OCR on the created image
    ocr_success = test_ocr_processing(test_image_path)
    
    # Test screenshot functionality (optional)
    if ocr_success:
        print("\n" + "="*50)
        print("Testing actual screenshot capture...")
        screenshot_path = test_screenshot_capture()
        
        if screenshot_path:
            # Try OCR on the actual screenshot
            print("\nTesting OCR on actual screenshot...")
            test_ocr_processing(screenshot_path)
    
    print("\n" + "="*60)
    print("Workflow test completed! 🎉")
    
    # Cleanup
    if os.path.exists("test_screenshots"):
        import shutil
        shutil.rmtree("test_screenshots")
    if os.path.exists("test_ocr_images"):
        shutil.rmtree("test_ocr_images")

if __name__ == "__main__":
    main()