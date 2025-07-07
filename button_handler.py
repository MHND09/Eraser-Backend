"""Button handler module for the smart whiteboard eraser."""

import os
import time
import logging
import threading
from config import (
    BUTTON_START_PAUSE_PIN,
    BUTTON_RESET_PIN,
    BUTTON_TOGGLE_SESSION_PIN,
    BUTTON_DEBOUNCE_MS,
    LOG_DIRECTORY,
    CMD_MOTOR_START_PAUSE,
    CMD_MOTOR_RESET,
    CMD_CAPTURE_AND_ERASE,
    CMD_SESSION
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIRECTORY, "button_handler.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ButtonHandler")

class ButtonHandler:
    """Handles physical button interactions for the smart whiteboard eraser."""
    
    def __init__(self, command_callback=None, motor_control=None):
        """Initialize the button handler."""
        self.command_callback = command_callback
        self.motor_control = motor_control
        self.running = False
        self.thread = None
        self.last_press_time = 0
        
        # Try to import GPIO or use a mock implementation when not on RPi
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.gpio_available = True
            logger.info("GPIO module loaded successfully")
        except ImportError:
            logger.warning("GPIO module not available. Using mock implementation.")
            self.gpio_available = False
    
    def setup_gpio(self):
        """Set up GPIO pins for buttons."""
        if not self.gpio_available:
            logger.warning("GPIO not available, skipping setup")
            return False
        
        try:
            self.GPIO.setmode(self.GPIO.BOARD)
            
            # Set up pins as inputs with pull-up resistors
            self.GPIO.setup(BUTTON_START_PAUSE_PIN, self.GPIO.IN, pull_up_down=self.GPIO.PUD_UP)
            self.GPIO.setup(BUTTON_RESET_PIN, self.GPIO.IN, pull_up_down=self.GPIO.PUD_UP)
            self.GPIO.setup(BUTTON_TOGGLE_SESSION_PIN, self.GPIO.IN, pull_up_down=self.GPIO.PUD_UP)
            logger.info("GPIO pins set up for button inputs")
            
            # Add event detection for falling edge (button pressed)
            self.GPIO.add_event_detect(BUTTON_START_PAUSE_PIN, self.GPIO.FALLING, 
                                     callback=lambda channel: self._button_callback(CMD_MOTOR_START_PAUSE), 
                                     bouncetime=BUTTON_DEBOUNCE_MS)
            
            self.GPIO.add_event_detect(BUTTON_RESET_PIN, self.GPIO.FALLING, 
                                     callback=lambda channel: self._button_callback(CMD_MOTOR_RESET), 
                                     bouncetime=BUTTON_DEBOUNCE_MS)
            
            self.GPIO.add_event_detect(BUTTON_TOGGLE_SESSION_PIN, self.GPIO.FALLING,
                                     callback=lambda channel: self._button_callback(CMD_SESSION), 
                                     bouncetime=BUTTON_DEBOUNCE_MS)

            logger.info("GPIO pins setup completed for motor control buttons")
            return True
        except Exception as e:
            logger.error(f"Error setting up GPIO pins: {e}")
            return False
    
    def _button_callback(self, command):
        """Handle button press events."""
        # Debounce manually in case the hardware debounce isn't sufficient
        current_time = time.time() * 1000  # Convert to milliseconds
        if current_time - self.last_press_time < BUTTON_DEBOUNCE_MS:
            return
        
        self.last_press_time = current_time
        logger.info(f"Button pressed: {command}")
        
        if command == CMD_SESSION:
            # Handle session toggle
            if self.command_callback:
                self.command_callback(CMD_SESSION)
            return

        # Handle motor commands directly if motor_control is available
        if self.motor_control and command == CMD_MOTOR_START_PAUSE:
            # Start/pause/resume logic - if starting, do capture and erase
            if not self.motor_control.motor_running and not self.motor_control.erasing:
                # Start with capture and erase
                if self.command_callback:
                    self.command_callback(CMD_CAPTURE_AND_ERASE)
            else:
                # Just handle start/pause
                response = self.motor_control.handle_start_pause()
                logger.info(f"Motor response: {response}")
        elif self.motor_control and command == CMD_MOTOR_RESET:
            response = self.motor_control.reset_motors()
            logger.info(f"Reset response: {response}")
        elif self.command_callback:
            # Fallback to command callback
            self.command_callback(command)
    
    def start(self):
        """Start the button handler."""
        if self.running:
            logger.warning("Button handler already running")
            return False
        
        self.running = True
        
        if self.gpio_available:
            success = self.setup_gpio()
            if not success:
                self.running = False
                return False
            logger.info("Button handler started with GPIO")
            return True
        else:
            # Start a thread to simulate button presses in development environments
            self.thread = threading.Thread(target=self._mock_button_monitor)
            self.thread.daemon = True
            self.thread.start()
            logger.info("Button handler started with mock implementation")
            return True
    
    def _mock_button_monitor(self):
        """Mock implementation for testing without GPIO."""
        logger.info("Mock button handler running. No physical buttons will be detected.")
        while self.running:
            time.sleep(1)  # Just keep the thread alive
    
    def stop(self):
        """Stop the button handler."""
        self.running = False
        
        if self.gpio_available:
            try:
                # Clean up GPIO
                self.GPIO.cleanup()
                logger.info("GPIO cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up GPIO: {e}")
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
            logger.info("Button handler stopped")
