"""Combined image queue and Drive uploader for the smart whiteboard eraser."""

import os
import time
import logging
import threading
import socket
import queue
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from supabase_handler import SupabaseHandler
from session import Session
from config import (
    CREDENTIALS_FILE, 
    TOKEN_FILE, 
    DRIVE_FOLDER_ID, 
    NETWORK_CHECK_INTERVAL, 
    UPLOAD_RETRY_INTERVAL, 
    LOG_DIRECTORY,
    QUEUE_DIRECTORY
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIRECTORY, "queue_uploader.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("QueueUploader")

class QueueUploader:
    """Combined image queue and Drive uploader class."""

    def __init__(self, queue_dir=QUEUE_DIRECTORY, supabase_handler:SupabaseHandler=None, session:Session=None):
        """Initialize the queue uploader."""
        self.queue_dir = queue_dir
        self.image_queue = queue.Queue()
        self.lock = threading.Lock()
        # Set to keep track of filepaths in the queue to avoid duplicates
        self.queue_paths = set()
        # Reference to the Supabase handler for database operations
        self.supabase_handler = supabase_handler
        # Reference to the Session object for tracking whiteboard sessions
        self.session = session
        
        # Upload thread management
        self.upload_thread = None
        self.running = False
        self.drive = None
        self.authenticated = False
        
        # Create queue directory if it doesn't exist
        if not os.path.exists(queue_dir):
            os.makedirs(queue_dir)
            
        # Load any existing files in the queue directory
        self._load_existing_files()
    
    def _load_existing_files(self):
        """Load any existing files in the queue directory into the queue."""
        with self.lock:
            try:
                for filename in sorted(os.listdir(self.queue_dir)):
                    if filename.endswith(('.jpg', '.jpeg', '.png')):
                        filepath = os.path.join(self.queue_dir, filename)
                        self.image_queue.put(filepath)
                        self.queue_paths.add(filepath)
                        logger.info(f"Loaded existing file into queue: {filepath}")
            except Exception as e:
                logger.error(f"Error loading existing files: {e}")
    
    def add_image(self, image_data):
        """Add a new image to the queue."""
        with self.lock:
            try:
                # Create a unique filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"whiteboard_{timestamp}.jpg"
                filepath = os.path.join(self.queue_dir, filename)
                
                # Save image to file
                with open(filepath, 'wb') as f:
                    f.write(image_data)
                
                # Add to queue
                self.image_queue.put(filepath)
                self.queue_paths.add(filepath)
                logger.info(f"Added new image to queue: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Error adding image to queue: {e}")
                return None
    
    def add_image_by_path(self, filepath):
        """Add an image to the queue by its file path, avoiding duplicates."""
        with self.lock:
            try:
                if filepath in self.queue_paths:
                    logger.info(f"Image already in queue, skipping: {filepath}")
                    return filepath
                
                # Add to queue and tracking set
                self.image_queue.put(filepath)
                self.queue_paths.add(filepath)
                logger.info(f"Added image path to queue: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Error adding image path to queue: {e}")
                return None
    
    def get_queue_size(self):
        """Return the current size of the queue."""
        return self.image_queue.qsize()
    
    # Google Drive Authentication and Upload Functions
    def authenticate(self):
        """Authenticate with Google Drive API."""
        try:
            gauth = GoogleAuth()
            # Try to load saved client credentials
            gauth.LoadCredentialsFile(TOKEN_FILE)
            
            if gauth.credentials is None:
                # Authenticate if they don't exist
                gauth.LocalWebserverAuth()
            elif gauth.access_token_expired:
                # Refresh them if expired
                gauth.Refresh()
            else:
                # Initialize the saved creds
                gauth.Authorize()
                
            # Save the current credentials to a file
            gauth.SaveCredentialsFile(TOKEN_FILE)
            self.drive = GoogleDrive(gauth)
            self.authenticated = True
            logger.info("Successfully authenticated with Google Drive")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.authenticated = False
            return False
    
    def check_internet_connection(self):
        """Check if there is an active internet connection."""
        try:
            # Try to connect to Google's DNS server
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False
    
    def upload_image(self, filepath):
        """Upload a single image to Google Drive."""
        if not self.authenticated and not self.authenticate():
            logger.error("Cannot upload: not authenticated")
            return False
        
        try:
            filename = os.path.basename(filepath)
            
            file_drive = self.drive.CreateFile({
                'title': filename,
                'parents': [{'id': DRIVE_FOLDER_ID}]
            })
            
            file_drive.SetContentFile(filepath)
            file_drive.Upload()
            
            # Get the URL of the uploaded file
            file_drive.FetchMetadata()
            img_id = file_drive.get('id')
            image_view_url = f"https://drive.usercontent.google.com/download?id={img_id}&export=view"
            
            logger.info(f"Successfully uploaded {filename} to Google Drive")
            
            # Insert to Supabase if handler is available
            if self.supabase_handler and image_view_url:
                logger.info(f"Adding image URL to Supabase: {image_view_url}")
                board_state_id = self.supabase_handler.add_image_to_db(image_view_url)
                if board_state_id:
                    # If a session is active, add this image to the session
                    if self.session and self.session.is_active():
                        logger.info(f"Adding image to active session {self.session.get_session_id()}")
                        if self.session.add_image_to_session(board_state_id):
                            logger.info(f"Successfully added image to session {self.session.get_session_id()}")
                        else:
                            logger.warning(f"Failed to add image to session {self.session.get_session_id()}")
                else:
                    logger.warning("Failed to get board state ID from Supabase")
            else:
                logger.warning("Supabase handler not available, skipping database insert")
            return True
        except Exception as e:
            logger.error(f"Error uploading {filepath}: {e}")
            return False
    
    def process_queue(self):
        """Process the image queue and upload images when internet is available."""
        while self.running:
            if self.check_internet_connection():
                # We have internet, try to upload images
                try:
                    filepath = self.image_queue.get(block=False)
                    # Remove from tracking set
                    self.queue_paths.discard(filepath)
                    
                    logger.info(f"Attempting to upload: {filepath}")
                    if self.upload_image(filepath):
                        # Successfully uploaded, remove from filesystem
                        try:
                            if os.path.exists(filepath):
                                os.remove(filepath)
                                logger.info(f"Removed image after upload: {filepath}")
                        except Exception as e:
                            logger.error(f"Error removing image: {e}")
                    else:
                        # Failed to upload, put it back in the queue
                        logger.warning(f"Upload failed, returning {filepath} to queue")
                        self.image_queue.put(filepath)
                        self.queue_paths.add(filepath)
                        # Wait before retrying
                        time.sleep(UPLOAD_RETRY_INTERVAL)
                except queue.Empty:
                    # Queue is empty, wait before checking again
                    logger.debug("Queue is empty, waiting...")
                    time.sleep(NETWORK_CHECK_INTERVAL)
            else:
                # No internet connection, wait before checking again
                logger.warning("No internet connection. Waiting...")
                time.sleep(NETWORK_CHECK_INTERVAL)
    
    def start(self):
        """Start the upload process in a background thread."""
        if not self.running:
            self.running = True
            self.authenticate()  # Try to authenticate immediately
            self.upload_thread = threading.Thread(target=self.process_queue)
            self.upload_thread.daemon = True
            self.upload_thread.start()
            logger.info("Upload process started")
    
    def stop(self):
        """Stop the upload process."""
        self.running = False
        if self.upload_thread:
            self.upload_thread.join(timeout=5)
            logger.info("Upload process stopped")