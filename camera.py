"""Camera module for the smart whiteboard eraser."""

import os
import logging
import subprocess
import time
from abc import ABC, abstractmethod
from datetime import datetime
from config import CAMERA_TYPE, CAMERA_DEVICE_INDEX, FSWEBCAM_OPTIONS, CAMERA_RESOLUTION, TEMP_IMAGE_PATH, QUEUE_DIRECTORY,LOG_DIRECTORY

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIRECTORY, "camera.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Camera")

class CameraInterface(ABC):
    """Abstract base class defining the interface for camera implementations."""
    
    @abstractmethod
    def initialize(self):
        """Initialize the camera."""
        pass
        
    @abstractmethod
    def capture_image(self):
        """Capture an image and return the binary data."""
        pass
    
    @abstractmethod
    def capture_and_save_image(self, queue_dir):
        """Capture an image and save it directly to the queue directory, returning the file path."""
        pass
    
    @abstractmethod
    def close(self):
        """Release camera resources."""
        pass

class PyGameCamera(CameraInterface):
    """Camera implementation using pygame.camera."""
    
    def __init__(self, device_index=0, resolution=(640, 480)):
        """Initialize pygame camera with the specified device and resolution."""
        self.device_index = device_index
        self.resolution = resolution
        self.camera = None
        
    def initialize(self):
        """Initialize the pygame camera."""
        try:
            import pygame
            import pygame.camera
            
            logger.info("Initializing PyGame camera module...")
            pygame.camera.init()
            camera_list = pygame.camera.list_cameras()
            
            if not camera_list:
                logger.error("No cameras found by pygame")
                return False
            
            if self.device_index >= len(camera_list):
                logger.error(f"Camera index {self.device_index} out of range. Available: {len(camera_list)}")
                return False
                
            logger.debug(f"Attempting to initialize camera with resolution: {self.resolution}")
            self.camera = pygame.camera.Camera(camera_list[self.device_index], self.resolution)
            self.camera.start()
            logger.info(f"PyGame camera initialized successfully: {camera_list[self.device_index]}")
            return True
        except ImportError as e:
            logger.error(f"Failed to import pygame: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize PyGame camera: {e}")
            return False
    
    def capture_image(self):
        """Capture an image using pygame camera."""
        if not self.camera:
            logger.error("Camera not initialized")
            return None
            
        try:
            # Give camera time to get ready
            time.sleep(0.5)
            
            # Capture the image
            image = self.camera.get_image()
            
            # Create a temporary path
            temp_path = os.path.join(TEMP_IMAGE_PATH, f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            # Save the image
            import pygame
            pygame.image.save(image, temp_path)
            
            # Read the binary data
            with open(temp_path, 'rb') as f:
                image_data = f.read()
                
            # Clean up
            os.remove(temp_path)
            
            logger.info("Image captured successfully using PyGame")
            return image_data
        except Exception as e:
            logger.error(f"Error capturing image with PyGame: {e}")
            return None
    
    def capture_and_save_image(self, queue_dir):
        """Capture an image and save it directly to the queue directory, returning the file path."""
        if not self.camera:
            logger.error("Camera not initialized")
            return None
            
        try:
            # Give camera time to get ready
            time.sleep(0.5)
            
            # Capture the image
            image = self.camera.get_image()
            
            # Create a unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"whiteboard_{timestamp}.jpg"
            filepath = os.path.join(queue_dir, filename)
            
            # Ensure the directory exists
            os.makedirs(queue_dir, exist_ok=True)
            
            # Save the image directly to the queue directory
            import pygame
            pygame.image.save(image, filepath)
            
            logger.info(f"Image captured and saved directly to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error capturing and saving image with PyGame: {e}")
            return None
    
    def close(self):
        """Release pygame camera resources."""
        if self.camera:
            try:
                self.camera.stop()
                logger.info("PyGame camera stopped")
            except Exception as e:
                logger.error(f"Error closing PyGame camera: {e}")

class FSWebcamCamera(CameraInterface):
    """Camera implementation using the fswebcam command-line tool."""
    
    def __init__(self, device="/dev/video0", resolution="640x480", options="--no-banner"):
        """Initialize fswebcam with the specified device, resolution and options."""
        self.device = device
        self.resolution = resolution
        self.options = options
        
    def initialize(self):
        """Check if fswebcam is available."""
        try:
            logger.info("Checking FSWebcam availability...")
            result = subprocess.run(["which", "fswebcam"], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("FSWebcam binary found")
                result = subprocess.run(["fswebcam"], capture_output=True, text=True)
                if result.returncode != 0 or "No such" in result.stderr.strip() or "No such" in result.stdout.strip():
                    logger.error("FSWebcam is not working correctly")
                    return False
                else:
                    logger.info(f"FSWebcam initialized with device: {self.device}, resolution: {self.resolution}")    
                    return True
            else:
                logger.error("FSWebcam command not found in system PATH")
                return False

        except Exception as e:
            logger.error(f"Error initializing FSWebcam: {e}")
            return False
    
    def capture_image(self):
        """Capture an image using fswebcam."""
        try:
            logger.debug("Starting FSWebcam image capture")
            # Create a temporary path
            temp_path = os.path.join(TEMP_IMAGE_PATH, f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            # Build the command
            cmd = ["fswebcam", "-d", self.device, "-r", self.resolution]
            if self.options:
                cmd.extend(self.options.split())
            cmd.append(temp_path)
                
            logger.debug(f"Executing FSWebcam command: {' '.join(cmd)}")
            # Execute the command
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FSWebcam error: {stderr.decode()}")
                return None
                
            # Read the binary data
            with open(temp_path, 'rb') as f:
                image_data = f.read()
                
            # Clean up
            os.remove(temp_path)
            
            logger.info("Image captured successfully using FSWebcam")
            return image_data
        except Exception as e:
            logger.error(f"Error capturing image with FSWebcam: {e}")
            return None
    
    def capture_and_save_image(self, queue_dir):
        """Capture an image and save it directly to the queue directory, returning the file path."""
        try:
            logger.debug("Starting FSWebcam direct image capture")
            # Create a unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"whiteboard_{timestamp}.jpg"
            filepath = os.path.join(queue_dir, filename)
            
            # Ensure the directory exists
            os.makedirs(queue_dir, exist_ok=True)
            
            # Build the command
            cmd = ["fswebcam", "-d", self.device, "-r", self.resolution]
            if self.options:
                cmd.extend(self.options.split())
            cmd.append(filepath)
            
            logger.debug(f"Executing FSWebcam command: {' '.join(cmd)}")
            # Execute the command
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FSWebcam error: {stderr.decode()}")
                return None
            
            logger.info(f"Image captured and saved directly to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error capturing and saving image with FSWebcam: {e}")
            return None
    
    def close(self):
        """Nothing to close for fswebcam."""
        pass

def create_camera():
    """Factory function to create the appropriate camera based on configuration."""
    if CAMERA_TYPE.lower() == "pygame":
        camera = PyGameCamera(
            device_index=CAMERA_DEVICE_INDEX,
            resolution=CAMERA_RESOLUTION
        )
    elif CAMERA_TYPE.lower() == "fswebcam":
        camera = FSWebcamCamera(
            device=f"/dev/video{CAMERA_DEVICE_INDEX}",
            resolution=f"{CAMERA_RESOLUTION[0]}x{CAMERA_RESOLUTION[1]}",
            options=FSWEBCAM_OPTIONS
        )
    else:
        logger.error(f"Unsupported camera type: {CAMERA_TYPE}")
        return None
        
    if camera.initialize():
        return camera
    
    return None
