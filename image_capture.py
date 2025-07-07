"""Image capture module for the smart whiteboard eraser."""

import os
import time
import logging
import threading
from datetime import datetime
from camera import create_camera
from config import QUEUE_DIRECTORY, LOG_DIRECTORY, CAPTURE_INTERVAL

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIRECTORY, "image_capture.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ImageCapture")

class ImageCapture:
    """Handles image capture and queueing for the smart whiteboard eraser system."""
    
    def __init__(self, queue_uploader, capture_interval=CAPTURE_INTERVAL):
        """Initialize the image capture service."""
        self.queue_uploader = queue_uploader
        self.capture_interval = capture_interval
        self.camera = create_camera()
        self.capture_thread = None
        self.running = False
        
        if not self.camera:
            logger.error("Failed to initialize camera")
    
    def start_continuous_capture(self):
        """Start continuous image capture in a background thread."""
        if not self.running and self.camera:
            self.running = True
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            logger.info("Continuous image capture started")
            return True
        else:
            logger.error("Cannot start continuous capture, camera not initialized or already running")
            return False
    
    def _capture_loop(self):
        """Internal method for continuous image capture."""
        while self.running:
            self.capture_image()
            
            # Sleep for the configured interval if it's greater than 0
            if self.capture_interval > 0:
                time.sleep(self.capture_interval)
    
    def capture_image(self):
        """Capture a single image and add it to the queue."""
        if not self.camera:
            logger.error("Camera not initialized")
            return False
        
        try:
            # Capture the image and save it directly to the queue directory
            filepath = self.camera.capture_and_save_image(QUEUE_DIRECTORY)
            if not filepath:
                logger.error("Failed to capture and save image")
                return False
            
            # Add to queue
            result = self.queue_uploader.add_image_by_path(filepath)
            if result:
                logger.info(f"Image captured and queued: {filepath}")
                return True
            else:
                logger.error("Failed to queue image path")
                return False
        except Exception as e:
            logger.error(f"Error during image capture: {e}")
            return False
    
    def stop(self):
        """Stop the image capture process."""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=5)
            logger.info("Image capture process stopped")
        
        # Close the camera
        if self.camera:
            self.camera.close()
            logger.info("Camera closed")
    
    def capture_single_image(self):
        """External method to trigger a single image capture."""
        return self.capture_image()