"""Motor control module for the smart whiteboard eraser."""

import os
import time
import logging
import threading
from config import (
    MOTOR1_PIN1, MOTOR1_PIN2, MOTOR1_PIN3, MOTOR1_PIN4,
    MOTOR2_PIN1, MOTOR2_PIN2, MOTOR2_PIN3, MOTOR2_PIN4,
    LOG_DIRECTORY
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIRECTORY, "motor_control.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MotorControl")

class MotorControl:
    """Controls the dual stepper motors for the whiteboard eraser."""
    
    def __init__(self):
        """Initialize the motor control."""
        self.running = False
        self.motor_running = False
        self.motor_paused = False
        self.reset_requested = False
        self.current_position = 0  # Track motor position for reset functionality
        self.motor_lock = threading.Lock()
        self.erasing = False
        self.erase_thread = None
        
        # Motor control pins - both motors work on X-axis in parallel
        self.motor1_pins = [MOTOR1_PIN1, MOTOR1_PIN2, MOTOR1_PIN3, MOTOR1_PIN4]
        self.motor2_pins = [MOTOR2_PIN1, MOTOR2_PIN2, MOTOR2_PIN3, MOTOR2_PIN4]
        
        # Halfstep sequence for stepper motors (same as wanted.py)
        self.halfstep_seq = [
            [1,0,0,0],
            [1,1,0,0],
            [0,1,0,0],
            [0,1,1,0],
            [0,0,1,0],
            [0,0,1,1],
            [0,0,0,1],
            [1,0,0,1]
        ]
        
        # Try to import GPIO or use a mock implementation when not on RPi
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.gpio_available = True
            logger.info("GPIO module loaded successfully for motor control")
        except ImportError:
            logger.warning("GPIO module not available. Using mock implementation for motor control.")
            self.gpio_available = False
    
    def setup_gpio(self):
        """Set up GPIO pins for motor control."""
        if not self.gpio_available:
            logger.warning("GPIO not available, skipping motor setup")
            return False
        
        try:
            self.GPIO.setmode(self.GPIO.BOARD)
            
            # Setup motor 1 pins as outputs
            for pin in self.motor1_pins:
                self.GPIO.setup(pin, self.GPIO.OUT)
                self.GPIO.output(pin, 0)
            
            # Setup motor 2 pins as outputs
            for pin in self.motor2_pins:
                self.GPIO.setup(pin, self.GPIO.OUT)
                self.GPIO.output(pin, 0)
            
            logger.info("GPIO setup completed for dual motor control")
            return True
        except Exception as e:
            logger.error(f"Error setting up motor GPIO pins: {e}")
            return False
    
    def move_motor_steps(self, steps, reverse=False):
        """Move both motors by specified number of steps in parallel"""
        if not self.gpio_available:
            logger.info(f"Mock: Moving both motors for {steps} steps, reverse={reverse}")
            time.sleep(steps * 0.001)  # Simulate movement time
            return
        
        sequence = self.halfstep_seq.copy()
        if reverse:
            sequence.reverse()
        
        for i in range(steps):
            # Check if we need to pause or reset
            if self.motor_paused:
                while self.motor_paused and not self.reset_requested:
                    time.sleep(0.01)
            
            if self.reset_requested:
                break
                
            # Execute one step on both motors simultaneously
            step_index = i % 8
            for pin in range(4):
                self.GPIO.output(self.motor1_pins[pin], sequence[step_index][pin])
                self.GPIO.output(self.motor2_pins[pin], sequence[step_index][pin])
            
            # Update position tracking
            if reverse:
                self.current_position -= 1
            else:
                self.current_position += 1
                
            time.sleep(0.001)
    def handle_start_pause(self):
        """Handle start/pause action - start erasing or toggle pause/resume"""
        if self.reset_requested:
            logger.warning("Please wait for reset to complete...")
            return "Please wait for reset to complete..."
            
        with self.motor_lock:
            if not self.erasing:
                # Start erasing
                logger.info("Starting erasing process...")
                return self.erase_whiteboard()
            else:
                # Toggle pause/resume for erasing operation
                self.motor_paused = not self.motor_paused
                if self.motor_paused:
                    logger.info("Erasing process paused")
                    return "Erasing process paused"
                else:
                    logger.info("Erasing process resumed")
                    return "Erasing process resumed"
    def reset_motors(self):
        """Reset both motors to original position"""
        logger.info("Resetting motors to original position...")
        
        # Stop current operation
        self.motor_running = False
        self.motor_paused = False
        self.erasing = False
        self.reset_requested = True
        
        # Wait for current erase thread to finish
        if self.erase_thread and self.erase_thread.is_alive():
            self.erase_thread.join(timeout=3)
        
        # Reset in separate thread
        reset_thread = threading.Thread(target=self._reset_process)
        reset_thread.daemon = True
        reset_thread.start()
        
        return "Reset initiated"
    
    def _reset_process(self):
        """Internal method to handle the reset process"""
        try:
            # Calculate steps needed to return to origin
            steps_to_return = abs(self.current_position)
            reverse_direction = self.current_position > 0
            
            if steps_to_return > 0:
                logger.info(f"Moving {steps_to_return} steps {'backward' if reverse_direction else 'forward'} to reset")
                self.reset_requested = False
                self.move_motor_steps(steps_to_return, reverse=reverse_direction)
                self.current_position = 0
                logger.info("Reset complete")
            else:
                logger.info("Already at original position")
                
        except Exception as e:
            logger.error(f"Error during reset process: {e}")
        finally:
            self.reset_requested = False
    
    def erase_whiteboard(self):
        """Erase the whiteboard by moving the eraser from one end to the other and back."""
        if self.erasing:
            logger.warning("Eraser is already in motion")
            return "Eraser is already in motion"
        
        self.erasing = True
        self.erase_thread = threading.Thread(target=self._erase_process)
        self.erase_thread.daemon = True
        self.erase_thread.start()
        
        return "Whiteboard erasing started"
    def _erase_process(self):
        """Internal method to handle the erasing process."""
        reset_during_forward = False
        try:
            logger.info("Starting whiteboard erasing process")
            self.motor_running = True
            self.motor_paused = False
            
            # Move forward across the whiteboard
            logger.info("Moving eraser forward")
            self.move_motor_steps(2000, reverse=False)  # Adjust steps as needed
            
            # Check if reset was requested during forward pass
            if self.reset_requested:
                reset_during_forward = True
                logger.info("Reset requested during forward pass, skipping backward pass")
            else:
                # Short pause at the end before backward pass
                time.sleep(0.5)
                
                # Move backward to complete the erasing only if no reset was requested
                if not self.reset_requested:
                    logger.info("Moving eraser backward")
                    self.move_motor_steps(2000, reverse=True)
            
            self.motor_running = False
            if not reset_during_forward:
                logger.info("Whiteboard erasing completed")
            else:
                logger.info("Whiteboard erasing interrupted by reset request")
        except Exception as e:
            logger.error(f"Error during erasing process: {e}")
        finally:
            self.erasing = False
            self.motor_running = False
    
    def stop_erasing(self):
        """Stop the erasing process."""
        if not self.erasing:
            return "No erasing process running"
            
        self.erasing = False
        if self.erase_thread and self.erase_thread.is_alive():
            self.erase_thread.join(timeout=5)
            logger.info("Erasing process stopped")
        
        return "Erasing process stopped"
    def get_status(self):
        """Get current motor status"""
        status = "STOPPED"
        if self.erasing:
            status = "PAUSED" if self.motor_paused else "ERASING"
        elif self.reset_requested:
            status = "RESETTING"
        
        return f"Motor: {status}, Position: {self.current_position} steps"
    
    def start(self):
        """Start the motor control service."""
        if self.running:
            logger.warning("Motor control already running")
            return False
        
        self.running = True
        
        if self.gpio_available:
            success = self.setup_gpio()
            if not success:
                self.running = False
                return False
        
        logger.info("Motor control started")
        return True
    def stop(self):
        """Stop the motor control service."""
        self.running = False
        self.erasing = False
        self.motor_running = False
        self.stop_erasing()
        
        if self.gpio_available:
            try:
                # Turn off all motor pins
                for pin in self.motor1_pins + self.motor2_pins:
                    self.GPIO.output(pin, 0)
                # Clean up GPIO
                self.GPIO.cleanup()
                logger.info("Motor GPIO pins cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up motor GPIO pins: {e}")
        
        logger.info("Motor control stopped")
