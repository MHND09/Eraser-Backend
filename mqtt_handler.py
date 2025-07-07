"""MQTT handler module for the smart whiteboard eraser."""

import os
import logging
import paho.mqtt.client as paho
from paho import mqtt
from config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_TOPIC,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    LOG_DIRECTORY,
    MQTT_COMMAND_TOPIC,
    MQTT_RESPONSE_TOPIC,
    MQTT_SESSION_TOPIC
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIRECTORY, "mqtt_handler.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MQTTHandler")

class MQTTHandler:
    """Handles MQTT communications for publishing board status."""
    
    def __init__(self, command_callback=None):
        """Initialize the MQTT handler."""
        self.mqtt_client = None
        self.command_callback = command_callback
        self.setup_mqtt_client()
    
    def setup_mqtt_client(self):
        """Set up the MQTT client for publishing board status."""
        logger.info("Setting up MQTT client")
        self.mqtt_client = paho.Client(paho.CallbackAPIVersion.VERSION2)
        self.mqtt_client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
        self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        # Set up callbacks
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        self.mqtt_client.on_publish = self.on_mqtt_publish
        self.mqtt_client.on_message = self.on_mqtt_message
        
        # Set last will message to be sent if connection drops unexpectedly
        self.mqtt_client.will_set(MQTT_TOPIC, payload="offline", qos=1, retain=True)
    
    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when MQTT client connects."""
        logger.info(f"MQTT client connected with code {rc}")
        # Publish online status when connected
        self.publish_board_status("online")
        
        # Subscribe to the command topic
        self.mqtt_client.subscribe(MQTT_COMMAND_TOPIC, qos=1)
        logger.info(f"Subscribed to command topic: {MQTT_COMMAND_TOPIC}")
    
    def on_mqtt_disconnect(self, client, userdata, flags, rc, properties=None):
        """Callback when MQTT client disconnects."""
        logger.info(f"MQTT client disconnected with code {rc}")
    
    def on_mqtt_publish(self, client, userdata, mid, reason_code, properties):
        """Callback when a message is published."""
        logger.debug(f"Published message with ID: {mid}")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Callback when a message is received."""
        logger.info(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
        
        if msg.topic == MQTT_COMMAND_TOPIC and self.command_callback:
            command = msg.payload.decode()
            logger.info(f"Processing command: {command}")
            self.command_callback(command)
    
    def publish_session_status(self, status):
        """Publish the session status to the MQTT session topic."""
        if not self.mqtt_client:
            logger.error("MQTT client not initialized")
            return False       
        try:
            result = self.mqtt_client.publish(MQTT_SESSION_TOPIC, payload=status, qos=1, retain=True)
            if result.rc == 0:
                logger.info(f"Published session status: {status}")
                return True
            else:
                logger.error(f"Failed to publish session status: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error publishing session status: {e}")
            return False

    def publish_board_status(self, status):
        """Publish the board status to the MQTT topic."""
        if not self.mqtt_client:
            logger.error("MQTT client not initialized")
            return False
            
        try:
            result = self.mqtt_client.publish(MQTT_TOPIC, payload=status, qos=1, retain=True)
            if result.rc == 0:
                logger.info(f"Published board status: {status}")
                return True
            else:
                logger.error(f"Failed to publish status: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error publishing status: {e}")
            return False
    
    def publish_response(self, message):
        """Publish a response message to the response topic."""
        if not self.mqtt_client:
            logger.error("MQTT client not initialized")
            return False
            
        try:
            result = self.mqtt_client.publish(MQTT_RESPONSE_TOPIC, payload=message, qos=1, retain=False)
            if result.rc == 0:
                logger.info(f"Published response: {message}")
                return True
            else:
                logger.error(f"Failed to publish response: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error publishing response: {e}")
            return False
    
    def start(self):
        """Start the MQTT client."""
        try:
            logger.debug(f"Attempting to connect to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            # Start the MQTT client in a non-blocking way
            self.mqtt_client.loop_start()
            logger.info("MQTT client connected and started")
            return True
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            return False
    
    def stop(self):
        """Stop the MQTT client."""
        if not self.mqtt_client:
            logger.debug("MQTT client not initialized, nothing to stop")
            return
            
        try:
            # Publish offline status before disconnecting
            logger.debug("Publishing offline status before disconnecting")
            self.publish_board_status("offline")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT client stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping MQTT client: {e}")
            logger.debug(f"Stack trace: {str(e)}")