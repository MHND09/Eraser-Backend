# Smart Whiteboard Eraser System

## Technical Overview
The Smart Whiteboard Eraser System is an IoT-based automation solution designed to streamline the whiteboard management process in educational and corporate environments. The system consists of a Raspberry Pi-controlled dual stepper motor mechanism that physically erases whiteboard content while providing advanced features including automated image capture, cloud storage, and scheduled operations.

This comprehensive system integrates hardware control with cloud services through a modular Python architecture,

## System Architecture

### Hardware Architecture
The system is built around the following hardware components:

#### Computational Core
- **Raspberry Pi**: Serves as the central processing unit, handling GPIO control, networking, and orchestration of all system operations.

#### Motor Control System
- **Dual Stepper Motors**: Configured in parallel on the X-axis with an 8-step sequence control pattern.
- **Motor Control Pins**:
  - Motor 1: GPIO pins 8, 10, 22, 3
  - Motor 2: GPIO pins 16, 18, 15, 13
- **Motion Control Algorithm**: Implements half-stepping sequence for precise positioning and smoother movement:
  ```
  [1,0,0,0], [1,1,0,0], [0,1,0,0], [0,1,1,0],
  [0,0,1,0], [0,0,1,1], [0,0,0,1], [1,0,0,1]
  ```

#### Input/Output Peripherals
- **Camera Module**: Supports multiple camera implementations:
  - FSWebcam (default): Configured at 1280x720 resolution
  - PyGame Camera: Alternative implementation for testing environments
- **Physical Interface**:
  - **Control Buttons**:
    - Start/Pause/Resume (GPIO 37)
    - Reset (GPIO 35)
    - Session Toggle (GPIO 33)
  - **Status LED** (GPIO 31): Visual indicator for system state

#### WebApp
#### Dashboard Admin Website
The system includes a web-based dashboard for remote control and monitoring of the whiteboard eraser. The dashboard provides the following features:

- **Real-Time Control**:
   - Execute MQTT commands such as `capture`, `erase`, and `status` directly from the web interface.
   - Toggle session states and manage motor operations remotely.

- **Data Visualization**:
   - Display session data retrieved from the Supabase database.
   - View captured whiteboard images and metadata.

- **Scheduler Management**:
   - Configure and manage automated tasks such as scheduled captures and erasures.
   - Enable or disable schedules dynamically.

- **System Monitoring**:
   - View real-time system status updates via MQTT.
   - Monitor logs and error reports for troubleshooting.
   The dashboard is built using modern web technologies, including Vite.js. It communicates with the system through MQTT and Supabase APIs for seamless integration.

### Software Architecture

#### Core Modules
The system follows a modular design pattern with the following key components:

1. **Motor Control Module (`motor_control.py`)**
   - Controls dual stepper motors with synchronized movement
   - Implements safety features including pause/resume functionality
   - Tracks motor position for reset operations
   - Thread-safe design with mutex locks for concurrent operations

2. **Camera Module (`camera.py`)**
   - Abstract base class (`CameraInterface`) with concrete implementations:
     - `PyGameCamera`: For testing in development environments
     - `FSWebcamCamera`: For production use with physical webcams
   - Methods for image capture, processing, and filesystem management

3. **Session Management Module (`session.py`)**
   - Tracks active whiteboard sessions
   - Interfaces with Supabase for session persistence
   - Maintains session state and metadata

4. **MQTT Communication Module (`mqtt_handler.py`)**
   - Implements publish-subscribe pattern for remote control
   - TLS-secured connections to HiveMQ cloud broker
   - Topic structure:
     - `eraser_{ID}/status`: System status updates
     - `eraser_{ID}/command`: Command reception channel
     - `eraser_{ID}/response`: Command acknowledgment
     - `eraser_{ID}/session`: Session state changes

5. **Scheduler Module (`scheduler.py`)**
   - Time-based task execution using the `schedule` library
   - Database-driven scheduling configuration
   - Support for recurring and one-time tasks

6. **Cloud Integration**
   - **Google Drive Upload (`queue_uploader.py`)**:
     - Asynchronous queue-based upload system
     - OAuth2 authentication
     - Automatic retry logic for network failures
   - **Supabase Database Integration (`supabase_handler.py`)**:
     - RESTful API communication
     - Real-time data synchronization
     - Structured data storage for system events and configurations

#### Communication Protocols
- **MQTT**: For remote command and control with QoS guarantees
- **HTTPS/REST**: For Supabase database operations
- **OAuth2**: For Google Drive API authentication

#### Concurrency Model
The system employs a multi-threaded architecture with:
- Thread synchronization via mutex locks
- Non-blocking I/O operations
- Thread-safe queues for inter-module communication

## Technical Specifications

### Performance Parameters
- **Image Resolution**: 1280×720 pixels (configurable)
- **Motor Control Precision**: 8-step half-stepping sequence
- **Button Debounce Time**: 300ms (configurable)
- **Network Check Interval**: 0.1 seconds
- **Upload Retry Interval**: 0.1 seconds

### Communication Protocol Details
- **MQTT Broker**: HiveMQ Cloud (TLS secured)
- **MQTT Port**: 8883 (standard secure MQTT port)
- **Authentication**: Username/password authentication
- **Topic Structure**: Hierarchical design with device ID isolation

### Software Dependencies
```
rpi-lgpio       # Raspberry Pi GPIO control
pygame          # Alternative camera implementation
supabase        # Database operations
paho-mqtt       # MQTT client implementation
PyDrive2        # Google Drive API wrapper
schedule        # Task scheduling
```

## Command API Reference

The system implements a comprehensive command API accessible via MQTT, physical buttons, or terminal input:

| Command | Description | Parameters | Response |
|---------|-------------|------------|----------|
| `capture` | Captures whiteboard image | None | Success/failure status |
| `erase` | Initiates erasing sequence | None | Motor operation status |
| `capture_erase` | Captures image then erases | None | Combined operation status |
| `stop` | Halts all operations | None | Stop confirmation |
| `status` | Reports system status | None | JSON status object |
| `session` | Toggles session state | None | Session status |
| `motor_start_pause` | Controls motor operation | None | Motor state |
| `motor_reset` | Returns motors to home position | None | Reset confirmation |
| `scheduler_reload` | Reloads schedules from database | None | Reload status |
| `scheduler_status` | Reports scheduler state | None | Scheduler status object |



## Database Schema

### Supabase Tables

The system uses a relational database model in Supabase with the following tables and relationships:

#### 1. Eraser Table
Records information about each eraser device:
- **id**: Unique identifier for each eraser device (primary key, auto-incrementing)
- **dateInstalled**: Timestamp when the eraser was installed
- **status**: Current operational status of the eraser
- **name**: Human-readable name assigned to the eraser
- **room**: Location where the eraser is installed
- **erasureCount**: Number of erasure operations performed

#### 2. Session Table
Tracks whiteboard usage sessions:
- **id**: Unique identifier for each session (primary key, auto-incrementing)
- **eraser**: Reference to the eraser device (foreign key to Eraser.id)
- **started_at**: Timestamp when the session was started
- **ended_at**: Timestamp when the session was ended (null if active)
- **summary**: Optional text summary of the session content

#### 3. Board_State Table
Stores metadata for captured whiteboard images:
- **id**: Unique identifier for each board state (primary key, auto-incrementing)
- **timestamp**: When the image was captured
- **imageUrl**: URL to the stored image in Google Drive
- **isComplete**: Boolean indicating if the whiteboard contains complete content
- **eraser**: Reference to the eraser device (foreign key to Eraser.id)
- **description**: Optional text description of the board content
- **tableContent**: Structured data extracted from tables on the whiteboard
- **labels**: Array of categorization labels for the content

#### 4. session_state Table
Junction table implementing a many-to-many relationship between sessions and board states:
- **id**: Unique identifier (primary key, auto-incrementing)
- **session**: Reference to a session (foreign key to Session.id)
- **state**: Reference to a board state (foreign key to Board_State.id)

#### 5. eraser_schedules Table
Configures automated erasure and capture schedules:
- **id**: Unique identifier for each schedule (primary key, auto-incrementing)
- **eraserid**: Reference to the eraser device (foreign key to Eraser.id)
- **tasktype**: Type of scheduled task ('capture', 'erase', or 'capture_erase')
- **scheduletype**: Scheduling pattern ('time', 'interval', or 'weekly')
- **schedulevalue**: Value specifying when to execute (format depends on scheduletype)
- **intervalunit**: Unit for interval schedules ('minutes', 'hours', or 'days')
- **isactive**: Boolean indicating if the schedule is currently active
- **description**: Human-readable description of the schedule
- **createdat**: When the schedule was created
- **lastrun**: When the schedule was last executed
- **nextrun**: When the schedule will next execute

#### 6. EraserLogs Table
Stores logs and events related to eraser operation:
- **id**: Unique identifier for each log entry (primary key, auto-incrementing)
- **eraserId**: Reference to the eraser device (foreign key to Eraser.id)
- **timestamp**: When the log entry was created
- **message**: Content of the log message


## Installation

### Hardware Setup
1. **Raspberry Pi Configuration**:
   - Flash Raspberry Pi OS (formerly Raspbian) to SD card
   - Enable SSH, I2C, and Camera interfaces via `raspi-config`
   - Connect to network and note IP address

2. **Motor Assembly**:
   - Connect stepper motors to motor driver boards
   - Wire motor drivers to GPIO pins as specified in `config.py`
   - Ensure proper power supply for motors (usually 5-12V DC)

3. **Peripheral Connection**:
   - Connect webcam to USB port
   - Wire buttons to specified GPIO pins with pull-down resistors
   - Connect LED to GPIO pin with appropriate current-limiting resistor

### Software Installation

1. **Install system dependencies**:
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-dev fswebcam
   ```

2. **Install Python requirements**:
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Configuration Setup**:
   - A Google Cloud project was created and enabled Drive API
   - Downloaded OAuth credentials as `client_secrets.json`
   - Created Supabase project
   - `config.py` settings store different settings:
     ```python
     # Supabase Credentials
     SUPABASE_URL = "supabase-url"
     SUPABASE_KEY = "supabase-key"
     
     # Google Drive settings
     DRIVE_FOLDER_ID = "the-google-drive-folder-id"
     ```

Note: queue uploader should automatically control updating session tokens when expired

### Directory Structure
```
├── button_handler.py    # Physical button interface
├── camera.py            # Camera abstraction and implementations
├── client_secrets.json  # Google API credentials
├── config.py            # System configuration
├── image_capture.py     # Image capture orchestration
├── led_control.py       # LED status indicators
├── log_publisher.py     # Log aggregation and cloud publishing
├── main.py              # System entry point
├── motor_control.py     # Stepper motor control
├── mqtt_handler.py      # MQTT communication
├── queue_uploader.py    # Asynchronous file upload
├── requirements.txt     # Python dependencies
├── schedule_manager.py  # Schedule creation and management
├── scheduler.py         # Task scheduling
├── session.py           # Session tracking
├── settings.yaml        # Additional configuration
├── supabase_handler.py  # Database operations
└── token.json           # Google OAuth tokens
```

## System Operation

### Initialization Sequence
1. Load configuration from `config.py`
2. Initialize hardware interfaces:
   - Set up GPIO pins for motors, buttons, and LEDs
   - Initialize camera module
3. Establish cloud connections:
   - Connect to MQTT broker
   - Authenticate with Supabase
   - Verify Google Drive credentials
4. Start background services:
   - Task scheduler
   - Upload queue processor
   - Button event listeners
   - MQTT subscription handlers

### Operation Flow
1. **Manual Operation**:
   - User presses physical button or sends MQTT command
   - System executes requested action (capture, erase, etc.)
   - Status updates published to MQTT and database

2. **Scheduled Operation**:
   - Scheduler polls database for scheduled tasks
   - At scheduled time, system executes configured action
   - Results and logs published to cloud services

3. **Image Capture and Processing**:
   - Camera captures image at specified resolution
   - Image saved temporarily to local filesystem
   - Image metadata recorded and added to upload queue

4. **Motor Operation**:
   - Motors receive step sequence commands
   - Position tracking maintained throughout operation
   - Safety checks prevent collisions and overruns

### Failsafe Mechanisms
- **Network Interruption Handling**:
  - Local queuing of captured images (images captured are saved in /queue and are picked up from there and deleted after upload)
  - Automatic retry with exponential backoff
  - Session state persistence

- **Power Failure Recovery**:
  - Non-volatile storage of system state (this garantees that the uploader picks up images which had issues uploading in the last run )
  - Graceful initialization after power restoration

- **Error Handling**:
  - Comprehensive logging with severity levels
  - Remote error reporting via MQTT
  - Automatic system recovery attempts

## Advanced Technical Features

### Concurrency Management
The system implements thread-safe operations through:
- Mutex locks for shared resource access
- Atomic operations for state changes
- Non-blocking I/O for network operations

### Extensibility
The modular architecture allows for:
- Alternative camera implementations
- Additional cloud service integrations
- Extended command API
- Custom scheduler plugins

### Testing Framework
- Mock GPIO implementation for development without hardware
- Simulated camera for image capture testing


## Performance Optimization

### CPU Usage Reduction
- Event-driven architecture minimizes polling
- Sleep intervals during idle periods

### Memory Management
- Proper resource cleanup after operations
- Minimal in-memory state maintenance


