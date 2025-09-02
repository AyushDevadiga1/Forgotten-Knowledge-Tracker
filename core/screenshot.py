import mss
import os
from datetime import datetime
import logging
from PIL import Image

logger = logging.getLogger(__name__)

class ScreenshotCapturer:
    def __init__(self, output_dir="screenshots"):
        """Initialize screenshot capturer"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.sct = None
        logger.info(f"Screenshot capturer initialized. Output directory: {output_dir}")
    
    def _get_sct_instance(self):
        """Get or create MSS instance with error handling"""
        try:
            if self.sct is None:
                self.sct = mss.mss()
            return self.sct
        except Exception as e:
            logger.error(f"Error creating MSS instance: {e}")
            # Try to recreate instance
            try:
                self.sct = mss.mss()
                return self.sct
            except Exception as e2:
                logger.error(f"Failed to recreate MSS instance: {e2}")
                return None
    
    def capture_screenshot(self, monitor=1):
        """Capture screenshot of specified monitor or primary monitor"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # Get MSS instance
            sct = self._get_sct_instance()
            if not sct:
                raise Exception("Could not initialize screenshot capturer")
            
            # Get monitor info - use primary monitor (index 1) by default
            monitors = sct.monitors
            if len(monitors) < 2:  # monitors[0] is all monitors combined
                raise Exception("No monitors detected")
            
            # Use specified monitor or primary
            if monitor >= len(monitors):
                monitor = 1  # Fallback to primary monitor
            
            monitor_info = monitors[monitor]
            
            # Capture screenshot
            screenshot = sct.grab(monitor_info)
            
            # Convert to PIL Image and save
            img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
            img.save(filepath, 'PNG')
            
            # Get file size for logging
            file_size = os.path.getsize(filepath)
            
            result = {
                'path': filepath,
                'filename': filename,
                'timestamp': timestamp,
                'size': screenshot.size,
                'file_size': file_size,
                'monitor': monitor
            }
            
            logger.info(f"Screenshot captured: {filename}")
            logger.info(f"Size: {screenshot.size[0]}x{screenshot.size[1]}, File size: {file_size} bytes")
            
            return result
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            # Try alternative capture method
            return self._fallback_capture(filepath, timestamp)
    
    def _fallback_capture(self, filepath, timestamp):
        """Fallback screenshot method using PIL ImageGrab"""
        try:
            from PIL import ImageGrab
            
            logger.info("Attempting fallback screenshot method...")
            
            # Capture using PIL ImageGrab
            screenshot = ImageGrab.grab()
            screenshot.save(filepath, 'PNG')
            
            file_size = os.path.getsize(filepath)
            
            result = {
                'path': filepath,
                'filename': os.path.basename(filepath),
                'timestamp': timestamp,
                'size': screenshot.size,
                'file_size': file_size,
                'monitor': 'primary'
            }
            
            logger.info(f"Fallback screenshot successful: {os.path.basename(filepath)}")
            return result
            
        except Exception as e:
            logger.error(f"Fallback screenshot failed: {e}")
            return None
    
    def capture_region(self, x, y, width, height):
        """Capture a specific region of the screen"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"region_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            sct = self._get_sct_instance()
            if not sct:
                raise Exception("Could not initialize screenshot capturer")
            
            # Define region
            region = {
                'top': y,
                'left': x,
                'width': width,
                'height': height
            }
            
            # Capture region
            screenshot = sct.grab(region)
            
            # Convert and save
            img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
            img.save(filepath, 'PNG')
            
            file_size = os.path.getsize(filepath)
            
            result = {
                'path': filepath,
                'filename': filename,
                'timestamp': timestamp,
                'size': screenshot.size,
                'file_size': file_size,
                'region': region
            }
            
            logger.info(f"Region screenshot captured: {filename}")
            return result
            
        except Exception as e:
            logger.error(f"Error capturing region screenshot: {e}")
            return None
    
    def cleanup_old_screenshots(self, max_age_hours=24, max_count=100):
        """Clean up old screenshots to save disk space"""
        try:
            import glob
            import time
            
            pattern = os.path.join(self.output_dir, "screenshot_*.png")
            files = glob.glob(pattern)
            
            # Sort by creation time (newest first)
            files.sort(key=lambda x: os.path.getctime(x), reverse=True)
            
            current_time = time.time()
            deleted_count = 0
            
            for i, file_path in enumerate(files):
                should_delete = False
                
                # Delete if too many files (keep only max_count newest)
                if i >= max_count:
                    should_delete = True
                
                # Delete if too old
                file_age_hours = (current_time - os.path.getctime(file_path)) / 3600
                if file_age_hours > max_age_hours:
                    should_delete = True
                
                if should_delete:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old screenshots")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during screenshot cleanup: {e}")
            return 0
    
    def get_available_monitors(self):
        """Get list of available monitors"""
        try:
            sct = self._get_sct_instance()
            if not sct:
                return []
            
            monitors = sct.monitors
            monitor_list = []
            
            for i, monitor in enumerate(monitors):
                if i == 0:  # Skip the combined monitor
                    continue
                    
                monitor_info = {
                    'index': i,
                    'width': monitor['width'],
                    'height': monitor['height'],
                    'left': monitor['left'],
                    'top': monitor['top']
                }
                monitor_list.append(monitor_info)
            
            return monitor_list
            
        except Exception as e:
            logger.error(f"Error getting monitor info: {e}")
            return []
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        if hasattr(self, 'sct') and self.sct:
            try:
                self.sct.close()
            except:
                pass