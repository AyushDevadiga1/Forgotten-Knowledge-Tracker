import pytest
import os
import time
from PIL import Image, ImageDraw
from core.screenshot import ScreenshotCapturer

class TestScreenshotCapturer:
    def setup_method(self):
        self.test_dir = "test_screenshots"
        self.capturer = ScreenshotCapturer(output_dir=self.test_dir)
    
    def teardown_method(self):
        # Clean up test files
        if os.path.exists(self.test_dir):
            for file in os.listdir(self.test_dir):
                os.remove(os.path.join(self.test_dir, file))
            os.rmdir(self.test_dir)
    
    def test_initialization(self):
        """Test that capturer initializes correctly"""
        assert os.path.exists(self.test_dir)
        assert self.capturer.capture_count == 0
        assert self.capturer.last_capture_time == 0
    
    def test_capture_screenshot(self):
        """Test screenshot capture functionality"""
        result = self.capturer.capture_screenshot("test_capture.png")
        
        assert result is not None
        assert os.path.exists(result['path'])
        assert self.capturer.capture_count == 1
        assert self.capturer.last_capture_time > 0
        
        # Verify the file is a valid image
        assert os.path.getsize(result['path']) > 0
        assert 'dimensions' in result
        assert 'timestamp' in result
    
    def test_get_capture_info(self):
        """Test capture information retrieval"""
        info = self.capturer.get_capture_info()
        
        assert info['total_captures'] == 0
        assert info['last_capture'] is None
        assert info['output_directory'] == self.test_dir
        
        # Capture and test again
        self.capturer.capture_screenshot()
        info = self.capturer.get_capture_info()
        
        assert info['total_captures'] == 1
        assert info['last_capture'] is not None
        assert info['directory_size'] >= 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])