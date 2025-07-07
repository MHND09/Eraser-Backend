"""Supabase handler module for the smart whiteboard eraser."""

import os
import logging
import threading
from supabase import create_client, Client
from config import LOG_DIRECTORY, SUPABASE_URL, SUPABASE_KEY, ID
import datetime
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIRECTORY, "supabase_handler.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SupabaseHandler")

class SupabaseHandler:
    """Handles Supabase database operations for the smart whiteboard eraser."""
    """
    Session schema: 
    id,eraser,started_at,ended_at

    Session_state: (many to many with Boardstate)
    id, session(sessionid), state(boardstateid)
    """
    
    def __init__(self):
        """Initialize the Supabase handler."""
        self.running = False
        self.client = None
    
    def create_session(self):
        """Create a new session in the Supabase database."""
        if not self.running:
            logger.warning("Supabase handler is not running, cannot create session")
            return False
        
        try:
            logger.info(" Creating new session in Supabase")
            started_at = datetime.datetime.now().astimezone().isoformat()
            response = self.client.from_("Session").insert({
                "eraser": ID,
                "started_at": started_at
            }).execute()
            logger.info("Successfully created session in Supabase")
            return response.data[0]['id']
        except Exception as e:
            logger.error(f"Error creating session in Supabase: {e}")
            return None

    def end_session(self, session_id):
        """End an existing session in the Supabase database."""
        if not self.running:
            logger.warning("Supabase handler is not running, cannot end session")
            return False
        
        try:
            logger.info(f"Ending session in Supabase: {session_id}")
            ended_at = datetime.datetime.now().astimezone().isoformat()
            response = self.client.from_("Session").update({
                "ended_at": ended_at
            }).eq("id", session_id).execute()
            logger.info(f"Successfully ended session in Supabase: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error ending session in Supabase: {e}")
            return False
    
    def add_image_to_session(self, session_id, board_state_id=None):
        """" Add an image URL to the current session in the Supabase database"""
        if not self.running:
            logger.warning("Supabase handler is not running, cannot add image to session")
            return False
        
        try:
            logger.info(f"Adding image to session in Supabase: {session_id}")
            # Use the most recent board state ID if none is provided
            if board_state_id is None:
                # Get the most recent board state for this eraser
                board_state = self.client.from_("Board_State").select("id").eq("eraser", ID).order("created_at", desc=True).limit(1).execute()
                if not board_state.data:
                    logger.error("No board state found to link to session")
                    return False
                board_state_id = board_state.data[0]['id']
                
            response = self.client.from_("session_state").insert({
                "session": session_id,
                "state": board_state_id
            }).execute()
            logger.info(f"Successfully added image to session in Supabase: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding image to session in Supabase: {e}")
            return False

    def add_image_to_db(self, image_url):
        """Add an image URL to the Supabase database and return the ID."""
        if not self.running:
            logger.warning("Supabase handler is not running, cannot add image URL to database")
            return False
        
        try:
            logger.info(f"Inserting image URL to Supabase: {image_url}")
            
            response = self.client.from_("Board_State").insert({
                "imageUrl": image_url,
                "eraser": ID
            }).execute()
            
            logger.info(f"Successfully inserted image URL to Supabase: {image_url}")
            # Return the ID of the inserted record for linking with sessions
            return response.data[0]['id']
        except Exception as e:
            logger.error(f"Error inserting to Supabase: {e}")
            logger.debug(f"Failed insertion details - URL: {image_url}, Eraser ID: {ID}")
            return None
    
    def start(self):
        """Start the Supabase handler."""
        if self.running:
            logger.warning("Supabase handler already running")
            return False
        
        try:
            # Initialize Supabase client
            self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
            self.running = True
            logger.info("Supabase handler started")
            return True
        except Exception as e:
            logger.error(f"Error initializing Supabase client: {e}")
            return False
    
    def stop(self):
        """Stop the Supabase handler."""
        if not self.running:
            return
            
        logger.info("Stopping Supabase handler")
        self.running = False
        self.client = None
        logger.info("Supabase handler stopped")
    
    def get_eraser_schedules(self, eraser_id=None):
        """Get active schedules for the specified eraser."""
        if not self.running:
            logger.warning("Supabase handler is not running, cannot fetch schedules")
            return []
        
        if eraser_id is None:
            eraser_id = ID
        
        try:
            logger.info(f"Fetching active schedules for eraser ID: {eraser_id}")
            response = self.client.from_("eraser_schedules").select("*").eq("eraserid", eraser_id).eq("isactive", True).execute()
            
            if response.data:
                logger.info(f"Found {len(response.data)} active schedules")
                return response.data
            else:
                logger.info("No active schedules found")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching schedules from Supabase: {e}")
            return []
    
    def update_schedule_last_run(self, schedule_id, last_run_time=None):
        """Update the last run timestamp for a schedule."""
        if not self.running:
            logger.warning("Supabase handler is not running, cannot update schedule")
            return False
        
        if last_run_time is None:
            last_run_time = datetime.datetime.now().astimezone().isoformat()
        
        try:
            logger.debug(f"Updating last run time for schedule {schedule_id}")
            response = self.client.from_("eraser_schedules").update({
                "lastrun": last_run_time
            }).eq("id", schedule_id).execute()
            
            logger.debug(f"Successfully updated last run time for schedule {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating last run time for schedule {schedule_id}: {e}")
            return False

if __name__ == "__main__":
    # Example usage
    handler = SupabaseHandler()
    if handler.start():
        session_id = handler.create_session()
        print(f"Session created with ID: {session_id}")