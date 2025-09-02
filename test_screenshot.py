#!/usr/bin/env python3
"""
Quick test to verify screenshot capture is working
"""
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_screenshot_capture():
    print("Testing Screenshot Capture Fix...")
    print("=" * 50)
    
    try:
        from core.screenshot import ScreenshotCapturer
        
        # Initialize capturer
        capturer = ScreenshotCapturer(output_dir="test_screenshots")
        print("✅ Screenshot capturer initialized")
        
        # Test monitor detection
        monitors = capturer.get_available_monitors()
        print(f"✅ Available monitors: {len(monitors)}")
        for i, monitor in enumerate(monitors):
            print(f"   Monitor {monitor['index']}: {monitor['width']}x{monitor['height']}")
        
        # Test screenshot capture
        print("\n🔄 Attempting screenshot capture...")
        result = capturer.capture_screenshot()
        
        if result:
            print(f"✅ Screenshot captured successfully!")
            print(f"   File: {result['filename']}")
            print(f"   Size: {result['size'][0]}x{result['size'][1]}")
            print(f"   File size: {result['file_size']} bytes")
            print(f"   Path: {result['path']}")
            
            # Verify file exists
            if os.path.exists(result['path']):
                print("✅ Screenshot file verified on disk")
            else:
                print("❌ Screenshot file not found on disk")
            
            return True
        else:
            print("❌ Screenshot capture failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during screenshot test: {e}")
        return False

def test_ocr_workflow():
    print("\n" + "=" * 50)
    print("Testing Complete Screenshot + OCR Workflow...")
    print("=" * 50)
    
    try:
        from core.screenshot import ScreenshotCapturer
        from core.ocr import OCRProcessor
        
        # Capture screenshot
        capturer = ScreenshotCapturer(output_dir="test_screenshots")
        result = capturer.capture_screenshot()
        
        if not result:
            print("❌ Could not capture screenshot for OCR test")
            return False
        
        print(f"✅ Screenshot captured: {result['filename']}")
        
        # Process with OCR
        ocr = OCRProcessor()
        ocr_result = ocr.extract_text_from_image(result['path'])
        
        print(f"✅ OCR processing completed")
        print(f"   Text length: {len(ocr_result['text'])} characters")
        print(f"   Word count: {ocr_result['word_count']}")
        print(f"   Confidence: {ocr_result.get('confidence', 'N/A')}%")
        
        if ocr_result['text']:
            preview = ocr_result['text'][:200] + "..." if len(ocr_result['text']) > 200 else ocr_result['text']
            print(f"   Text preview: {preview}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in OCR workflow test: {e}")
        return False

def main():
    print("🔧 Screenshot Fix Verification Tool")
    print("=" * 50)
    
    success = True
    
    # Test basic screenshot capture
    if not test_screenshot_capture():
        success = False
    
    # Test complete workflow
    if not test_ocr_workflow():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Screenshot capture is working correctly.")
        print("\nYou can now run: python run_tracker.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()