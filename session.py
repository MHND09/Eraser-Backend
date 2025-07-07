"""Session management module for the smart whiteboard eraser."""

import logging
import os
from config import LOG_DIRECTORY
from supabase_handler import SupabaseHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIRECTORY, "session.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SessionManager")

class Session:
    """Manages session state for the smart whiteboard eraser."""
    
    def __init__(self, supabase_handler:SupabaseHandler=None):
        """Initialize the session manager."""
        self.supabase_handler = supabase_handler
        self.active = False
        self.session_id = None
        logger.info("Session manager initialized")
    
    def start(self):
        """Start a new session."""
        if self.active:
            logger.warning("Session already active, cannot start a new one")
            return False, "Session already active"
        
        if not self.supabase_handler:
            logger.error("No Supabase handler available, cannot start session")
            return False, "No database connection available"
        
        session_id = self.supabase_handler.create_session()
        if session_id:
            self.active = True
            self.session_id = session_id
            logger.info(f"Session started with ID: {session_id}")
            return True, f"Session started with ID: {session_id}"
        else:
            logger.error("Failed to create session")
            return False, "Failed to create session"
    
    def end(self):
        """End the current session."""
        if not self.active:
            logger.warning("No active session to end")
            return False, "No active session"
        
        if not self.supabase_handler:
            logger.error("No Supabase handler available, cannot end session")
            return False, "No database connection available"
        
        if self.supabase_handler.end_session(self.session_id):
            logger.info(f"Session ended: {self.session_id}")
            self.active = False
            self.session_id = None
            return True, "Session ended successfully"
        else:
            logger.error(f"Failed to end session: {self.session_id}")
            return False, "Failed to end session"
    
    def toggle(self):
        """Toggle session state (start if not active, end if active)."""
        if self.active:
            return self.end()
        else:
            return self.start()
    
    def add_image_to_session(self, board_state_id):
        """Add an image to the current session."""
        if not self.active:
            logger.debug("No active session, skipping image association")
            return False
        
        if not self.supabase_handler:
            logger.error("No Supabase handler available, cannot add image to session")
            return False
        
        logger.info(f"Adding image to session {self.session_id} with board state ID: {board_state_id}")
        return self.supabase_handler.add_image_to_session(self.session_id, board_state_id)
    
    def is_active(self):
        """Return whether a session is currently active."""
        return self.active
    
    def get_session_id(self):
        """Return the current session ID or None if no session is active."""
        return self.session_id if self.active else None
