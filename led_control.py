"""LED control module for the smart whiteboard eraser."""

import logging
import os
from config import LOG_DIRECTORY, LED_SESSION_PIN

# Setup logging
if not os.path.exists(LOG_DIRECTORY):
    os.makedirs(LOG_DIRECTORY)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIRECTORY, "led_control.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LEDControl")

class LEDControl:
    """Controls LED indicators for system status."""
    
    def __init__(self):
        """Initialize the LED control module."""
        logger.info("Initializing LED Control")
        
        self.GPIO = None
        self.gpio_available = False

        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.gpio_available = True
            logger.info("GPIO module loaded successfully")
            
            # Set up GPIO
            self.GPIO.setwarnings(False)
            self.GPIO.setmode(self.GPIO.BOARD)
            
            # Set up LED pins
            self.GPIO.setup(LED_SESSION_PIN, self.GPIO.OUT)
            
            # Initialize all LEDs to off state
            self.session_led_off()
            
        except ImportError:
            logger.warning("GPIO module not available. LED control will be mocked.")
            # self.session_led_off() # Called implicitly by doing nothing if GPIO not available

        logger.info("LED Control initialized")
    
    def session_led_on(self):
        """Turn on the session LED to indicate active session."""
        try:
            if not self.gpio_available:
                logger.debug("GPIO not available, mocking Session LED ON")
                return True
            self.GPIO.output(LED_SESSION_PIN, self.GPIO.HIGH)
            logger.debug("Session LED turned ON")
            return True
        except Exception as e:
            logger.error(f"Error turning session LED on: {e}")
            return False
    
    def session_led_off(self):
        """Turn off the session LED to indicate no active session."""
        try:
            if not self.gpio_available:
                logger.debug("GPIO not available, mocking Session LED OFF")
                return True
            self.GPIO.output(LED_SESSION_PIN, self.GPIO.LOW)
            logger.debug("Session LED turned OFF")
            return True
        except Exception as e:
            logger.error(f"Error turning session LED off: {e}")
            return False
    
    def update_session_led(self, session_active):
        """Update the session LED based on session state."""
        if session_active:
            return self.session_led_on()
        else:
            return self.session_led_off()
    
    def stop(self):
        """Clean up GPIO pins when stopping."""
        try:
            # Turn off all LEDs
            self.session_led_off()
            if self.gpio_available and self.GPIO:
                self.GPIO.cleanup()
                logger.info("GPIO cleaned up")
            logger.info("LED Control stopped")
        except Exception as e:
            logger.error(f"Error stopping LED Control: {e}")
