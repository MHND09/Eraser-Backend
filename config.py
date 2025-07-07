"""Configuration settings for the smart whiteboard eraser."""

# Eraser ID for mqtt comms
ID = 1

# Path settings
QUEUE_DIRECTORY = "queue"
LOG_DIRECTORY = "logs"
TEMP_IMAGE_PATH = "temp"

# Google Drive settings
CREDENTIALS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
DRIVE_FOLDER_ID = ""

# Network settings
NETWORK_CHECK_INTERVAL = 0.1  # seconds
UPLOAD_RETRY_INTERVAL = 0.1  # seconds

# Camera settings
CAMERA_TYPE = "fswebcam"
CAMERA_DEVICE_INDEX = 0
CAMERA_RESOLUTION = (1280, 720)
FSWEBCAM_OPTIONS = "--no-banner --jpeg 85"
CAPTURE_INTERVAL = 0

# MQTT settings
MQTT_BROKER = "1c1ede3b166543d4823c1c3f26a82bad.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_TOPIC = f"eraser_{ID}/status"
MQTT_COMMAND_TOPIC = f"eraser_{ID}/command"
MQTT_RESPONSE_TOPIC = f"eraser_{ID}/response"
MQTT_SESSION_TOPIC = f"eraser_{ID}/session"
MQTT_USERNAME = ""
MQTT_PASSWORD = ""

# Commands
CMD_CAPTURE = "capture"
CMD_ERASE = "erase"
CMD_CAPTURE_AND_ERASE = "capture_erase"
CMD_STOP = "stop"
CMD_STATUS = "status"
CMD_SESSION = "session"
CMD_MOTOR_START_PAUSE = "motor_start_pause"
CMD_MOTOR_RESET = "motor_reset"
CMD_MOTOR_PAUSE_RESUME = "motor_pause_resume"
CMD_SCHEDULER_RELOAD = "scheduler_reload"
CMD_SCHEDULER_STATUS = "scheduler_status"

# Button GPIO pin configurations
BUTTON_START_PAUSE_PIN = 37  # GPIO pin for start/pause/resume motor button
BUTTON_RESET_PIN = 35        # GPIO pin for reset motor button
BUTTON_TOGGLE_SESSION_PIN = 33  # GPIO pin for start session button
# Button debounce time in milliseconds
BUTTON_DEBOUNCE_MS = 300

LED_SESSION_PIN = 31
# Motor control pins for two stepper motors
# Motor 1 control pins 
MOTOR1_PIN1 = 8
MOTOR1_PIN2 = 10
MOTOR1_PIN3 = 22
MOTOR1_PIN4 = 3

# Motor 2 control pins 
MOTOR2_PIN1 = 16
MOTOR2_PIN2 = 18
MOTOR2_PIN3 = 15
MOTOR2_PIN4 = 13

# Supabase Creds
SUPABASE_URL = "https://your-supabase-url.supabase.co"
SUPABASE_KEY = "your-supabase-key"