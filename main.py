"""Main entry point for the smart whiteboard eraser system."""

import os
import logging
import signal
import sys
import time
import threading
import subprocess
from queue_uploader import QueueUploader
from image_capture import ImageCapture
from mqtt_handler import MQTTHandler
from button_handler import ButtonHandler
from motor_control import MotorControl
from supabase_handler import SupabaseHandler
from session import Session
from led_control import LEDControl
from scheduler import TaskScheduler
from config import (
    LOG_DIRECTORY,
    CMD_CAPTURE,
    CMD_ERASE,
    CMD_CAPTURE_AND_ERASE,
    CMD_STOP,
    CMD_STATUS,
    CMD_SESSION,
    CMD_MOTOR_START_PAUSE,
    CMD_MOTOR_RESET,
    CMD_MOTOR_PAUSE_RESUME,
    CMD_SCHEDULER_RELOAD,
    CMD_SCHEDULER_STATUS,
)


if not os.path.exists(LOG_DIRECTORY):
    os.makedirs(LOG_DIRECTORY)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIRECTORY, "main.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MainService")

class SmartEraserService:
    def __init__(self):
        """Initialize the smart eraser service."""
        logger.info("Initializing Smart Whiteboard Eraser Service")
        
        # Initialize the Supabase handler
        self.supabase_handler = SupabaseHandler()
        
        # Initialize the session manager
        self.session = Session(supabase_handler=self.supabase_handler)
        
        # Initialize the combined queue and uploader with Supabase handler
        self.queue_uploader = QueueUploader(supabase_handler=self.supabase_handler, session=self.session)
          # Initialize the image capture service
        self.image_capture = ImageCapture(self.queue_uploader)
        
        # Initialize the LED control
        self.led_control = LEDControl()
        
        # Initialize the motor control
        self.motor_control = MotorControl()
        
        # Initialize the MQTT handler with command callback
        self.mqtt_handler = MQTTHandler(command_callback=self.handle_command)        # Initialize the button handler with command callback and motor control
        self.button_handler = ButtonHandler(command_callback=self.handle_command, motor_control=self.motor_control)
        
        # Initialize the task scheduler
        self.task_scheduler = TaskScheduler(supabase_handler=self.supabase_handler, command_callback=self.handle_command)
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.running = False
        self.input_thread = None
    
    def signal_handler(self, sig, frame):
        """Handle termination signals for graceful shutdown."""
        logger.info(f"Received signal {sig}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def handle_command(self, command):
        """Handle commands from various sources (MQTT, buttons, CLI)."""
        logger.info(f"Handling command: {command}")
        
        # Normalize the command
        command = command.lower().strip()

        if command == CMD_CAPTURE:
            # Capture image
            logger.debug("Processing capture image command")
            success = self.capture_image()
            response = "Image captured successfully" if success else "Failed to capture image"
            logger.info(f"Capture command result: {response}")
        elif command == CMD_SESSION:
            # Toggle session state using the session manager
            logger.debug("Processing session toggle command")
            success, message = self.session.toggle()
            
            # Update the session LED based on current session state
            if success:
                session_active = self.session.is_active()
                led_status = self.led_control.update_session_led(session_active)
                logger.debug(f"Session LED {'activated' if session_active else 'deactivated'}: {led_status}")
                session_status = "active" if session_active else "not active"
                self.mqtt_handler.publish_session_status(session_status)
            response = message
            logger.info(f"Session command result: {response}")
        
        elif command == CMD_ERASE:
            # Erase whiteboard
            logger.debug("Processing erase whiteboard command")
            success = self.erase_whiteboard()
            response = "Erasing whiteboard" if success else "Failed to start erasing"
            logger.info(f"Erase command result: {response}")
            
        elif command == CMD_CAPTURE_AND_ERASE:
            # Capture image and then erase
            logger.debug("Processing capture and erase command")
            img_success = self.capture_image()
            erase_success = self.erase_whiteboard()
            
            if img_success and erase_success:
                response = "Image captured, now erasing whiteboard"
            elif img_success:
                response = "Image captured, but failed to start erasing"
            elif erase_success:
                response = "Failed to capture image, but erasing whiteboard"
            else:
                response = "Failed to capture image and erase whiteboard"
            logger.info(f"Capture and erase command result: {response}")
                
        elif command == CMD_STOP:
            # Stop any ongoing processes
            logger.debug("Processing stop command")
            self.motor_control.stop_erasing()
            response = "Stopped all operations"
            logger.info("Stop command executed")
        elif command == CMD_STATUS:
            # Get system status
            logger.debug("Processing status request")
            scheduler_status = self.task_scheduler.get_status()
            status = {
                "queue_size": self.queue_uploader.get_queue_size(),
                "erasing": self.motor_control.erasing,
                "internet": self.queue_uploader.check_internet_connection(),
                "session_active": self.session.is_active(),
                "scheduler": {
                    "running": scheduler_status.get("running", False),
                    "active_jobs": scheduler_status.get("active_jobs", 0),
                    "cached_schedules": scheduler_status.get("cached_schedules", 0)
                }
            }
            response = f"Status: {status}"
            logger.info(f"Status request result: {status}")
            
        elif command == CMD_MOTOR_START_PAUSE:
            # Handle motor start/pause/resume
            logger.debug("Processing motor start/pause command")
            response = self.motor_control.handle_start_pause()
            logger.info(f"Motor start/pause command result: {response}")
            
        elif command == CMD_MOTOR_RESET:
            # Handle motor reset
            logger.debug("Processing motor reset command")
            response = self.motor_control.reset_motors()
            logger.info(f"Motor reset command result: {response}")
        elif command == CMD_MOTOR_PAUSE_RESUME:
            # Handle motor pause/resume toggle
            logger.debug("Processing motor pause/resume command")
            if self.motor_control.motor_running:
                self.motor_control.motor_paused = not self.motor_control.motor_paused
                response = "Motors paused" if self.motor_control.motor_paused else "Motors resumed"
            else:
                response = "Motors are not running"
            logger.info(f"Motor pause/resume command result: {response}")
            
        elif command == CMD_SCHEDULER_RELOAD:
            # Reload schedules from database
            logger.debug("Processing scheduler reload command")
            try:
                self.task_scheduler.reload_schedules()
                response = "Schedules reloaded successfully"
                logger.info("Scheduler reload command executed successfully")
            except Exception as e:
                response = f"Failed to reload schedules: {str(e)}"
                logger.error(f"Scheduler reload command failed: {e}")
                
        elif command == CMD_SCHEDULER_STATUS:
            # Get detailed scheduler status
            logger.debug("Processing scheduler status request")
            try:
                scheduler_status = self.task_scheduler.get_status()
                response = f"Scheduler Status: {scheduler_status}"
                logger.info(f"Scheduler status request result: {scheduler_status}")
            except Exception as e:
                response = f"Failed to get scheduler status: {str(e)}"
                logger.error(f"Scheduler status request failed: {e}")
            
        else:
            logger.warning(f"Unknown command received: {command}")
            response = f"Unknown command: {command}"
        
        # Publish the response via MQTT
        logger.debug(f"Publishing response: {response}")
        self.mqtt_handler.publish_response(response)
        
        return response
    def capture_image(self):
        """Trigger an image capture."""
        return self.image_capture.capture_single_image()
    
    def erase_whiteboard(self):
        """Trigger whiteboard erasing."""
        return self.motor_control.erase_whiteboard()
    def _process_keyboard_input(self):
        """Handle keyboard input for commands."""
        print("\nCommand options:")
        print("  c - Capture image")
        print("  e - Erase whiteboard")
        print("  b - Capture image and erase whiteboard")
        print("  m - Start/Pause/Resume motor")
        print("  r - Reset motor to original position")
        print("  s - Stop operations")
        print("  i - Show system information")
        print("  n - Toggle session (start/stop)")
        print("  l - Reload schedules from database")
        print("  j - Show scheduler status")
        print("  q - Quit")
        
        while self.running:
            try:
                user_input = input("\nEnter command: ").lower().strip()
                
                if user_input == 'c':
                    self.handle_command(CMD_CAPTURE)
                elif user_input == 'e':
                    self.handle_command(CMD_ERASE)
                elif user_input == 'b':
                    self.handle_command(CMD_CAPTURE_AND_ERASE)
                elif user_input == 'm':
                    self.handle_command(CMD_MOTOR_START_PAUSE)
                elif user_input == 'r':
                    self.handle_command(CMD_MOTOR_RESET)
                elif user_input == 's':
                    self.handle_command(CMD_STOP)
                elif user_input == 'i':
                    self.handle_command(CMD_STATUS)                
                elif user_input == 'n':
                    self.handle_command(CMD_SESSION)
                elif user_input == 'l':
                    self.handle_command(CMD_SCHEDULER_RELOAD)
                elif user_input == 'j':
                    self.handle_command(CMD_SCHEDULER_STATUS)
                elif user_input == 'q':
                    print("Shutting down...")
                    self.stop()
                    break
                else:
                    print(f"Unknown command: {user_input}")
                    
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error processing keyboard input: {e}")
    
    def start(self):
        """Start the service."""
        logger.info("Starting Smart Whiteboard Eraser Service")
        self.running = True

        # Start the log publisher as a background process
        try:
            log_publisher_path = os.path.join(os.path.dirname(__file__), "log_publisher.py")
            self.log_publisher_proc = subprocess.Popen([
                sys.executable, log_publisher_path
            ])
            logger.info("Log publisher started as a background process")
        except Exception as e:
            logger.error(f"Failed to start log publisher: {e}")
            self.log_publisher_proc = None        # Start the Supabase handler
        self.supabase_handler.start()
        
        #self.session.start()
        
        # Initialize LED state based on current session status
        session_active = self.session.is_active()
        session_status = "active" if session_active else "not active"
        self.mqtt_handler.publish_session_status(session_status)
        self.led_control.update_session_led(session_active)
        logger.info(f"LED initialized to {'ON' if session_active else 'OFF'} based on session state")

        # Start the queue uploader
        self.queue_uploader.start()
        
        # Start the MQTT handler
        self.mqtt_handler.start()
        
        # Start the button handler
        self.button_handler.start()
          # Start the motor control
        self.motor_control.start()
        
        # Start the task scheduler
        self.task_scheduler.start()
        
        # Start keyboard input processing in a separate thread
        self.input_thread = threading.Thread(target=self._process_keyboard_input)
        self.input_thread.daemon = True
        self.input_thread.start()
        
        try:
            # Keep the main thread alive
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in main service loop: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the service."""
        if not self.running:
            logger.debug("Service already stopped")
            return
        logger.info("Stopping Smart Whiteboard Eraser Service")        
        self.running = False        # Stop all services
        self.task_scheduler.stop()
        self.session.end()
        self.motor_control.stop()
        self.button_handler.stop()
        self.mqtt_handler.stop()
        self.image_capture.stop()        
        self.queue_uploader.stop()
        self.supabase_handler.stop()
        self.led_control.stop()

        # Stop the log publisher process if running
        if hasattr(self, 'log_publisher_proc') and self.log_publisher_proc:
            try:
                self.log_publisher_proc.terminate()
                self.log_publisher_proc.wait(timeout=5)
                logger.info("Log publisher process terminated")
            except Exception as e:
                logger.error(f"Error terminating log publisher: {e}")

        logger.info("All services stopped")

# Run the service when this script is executed
if __name__ == "__main__":
    service = SmartEraserService()
    service.start()
