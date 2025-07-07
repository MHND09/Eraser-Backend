"""Scheduler module for the smart whiteboard eraser system."""

import os
import logging
import threading
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Callable
from config import LOG_DIRECTORY, ID

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIRECTORY, "scheduler.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Scheduler")


class TaskScheduler:
    """Handles scheduled tasks from Supabase database."""
    
    def __init__(self, supabase_handler, command_callback: Callable[[str], str]):
        """
        Initialize the task scheduler.
        
        Args:
            supabase_handler: The Supabase handler instance
            command_callback: Callback function to execute commands
        """
        self.supabase_handler = supabase_handler
        self.command_callback = command_callback
        self.running = False
        self.scheduler_thread = None
        self.schedules_cache = {}
        self.eraser_id = ID
        
    def fetch_schedules(self) -> List[Dict]:
        """Fetch active schedules from Supabase for this eraser."""
        if not self.supabase_handler.running:
            logger.warning("Supabase handler is not running, cannot fetch schedules")
            return []
        
        try:
            logger.info(f"Fetching schedules for eraser ID: {self.eraser_id}")
            response = self.supabase_handler.client.from_("eraser_schedules").select("*").eq("eraserid", self.eraser_id).eq("isactive", True).execute()
            
            if response.data:
                logger.info(f"Found {len(response.data)} active schedules")
                return response.data
            else:
                logger.info("No active schedules found")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching schedules from Supabase: {e}")
            return []
    
    def update_last_run(self, schedule_id: int):
        """Update the last run timestamp for a schedule."""
        try:
            current_time = datetime.now().astimezone().isoformat()
            self.supabase_handler.client.from_("eraser_schedules").update({
                "lastrun": current_time
            }).eq("id", schedule_id).execute()
            logger.debug(f"Updated last run time for schedule {schedule_id}")
        except Exception as e:
            logger.error(f"Error updating last run time for schedule {schedule_id}: {e}")
    
    def execute_scheduled_task(self, schedule_data: Dict):
        """Execute a scheduled task and update the database."""
        task_type = schedule_data.get('tasktype')
        schedule_id = schedule_data.get('id')
        description = schedule_data.get('description', '')
        
        logger.info(f"Executing scheduled task: {task_type} (ID: {schedule_id}) - {description}")
        
        try:
            # Execute the command using the callback
            result = self.command_callback(task_type)
            logger.info(f"Scheduled task {task_type} executed successfully: {result}")
            
            # Update the last run time in the database
            self.update_last_run(schedule_id)
            
        except Exception as e:
            logger.error(f"Error executing scheduled task {task_type} (ID: {schedule_id}): {e}")
    
    def parse_schedule_value(self, schedule_type: str, schedule_value: str, interval_unit: str = None) -> str:
        """
        Parse schedule value based on schedule type.
        
        Args:
            schedule_type: 'time', 'interval', or 'weekly'
            schedule_value: The schedule value from database
            interval_unit: For interval schedules: 'minutes', 'hours', 'days'
            
        Returns:
            Parsed schedule string for the schedule library
        """
        if schedule_type == 'time':
            # Format: "HH:MM" (e.g., "14:30")
            return schedule_value.strip()
        elif schedule_type == 'interval':
            # Format: number + unit (e.g., "30" with interval_unit "minutes")
            try:
                interval_value = int(schedule_value)
                return f"{interval_value}_{interval_unit}"
            except ValueError:
                logger.error(f"Invalid interval value: {schedule_value}")
                return None
        elif schedule_type == 'weekly':
            # Format: "MONDAY", "TUESDAY", etc. with optional time "MONDAY:14:30"
            parts = schedule_value.strip().split(':')
            if len(parts) >= 1:
                day = parts[0].lower()
                time_part = ':'.join(parts[1:]) if len(parts) > 1 else "09:00"
                return f"{day}_{time_part}"
            return None
        else:
            logger.error(f"Unknown schedule type: {schedule_type}")
            return None
    
    def setup_schedule(self, schedule_data: Dict):
        """Set up a single schedule based on its configuration."""
        schedule_type = schedule_data.get('scheduletype')
        schedule_value = schedule_data.get('schedulevalue')
        interval_unit = schedule_data.get('intervalunit')
        schedule_id = schedule_data.get('id')
        task_type = schedule_data.get('tasktype')
        description = schedule_data.get('description', '')
        
        logger.info(f"Setting up schedule {schedule_id}: {schedule_type} - {schedule_value} - {task_type}")
        
        parsed_schedule = self.parse_schedule_value(schedule_type, schedule_value, interval_unit)
        if not parsed_schedule:
            logger.error(f"Failed to parse schedule for ID {schedule_id}")
            return
        
        try:
            if schedule_type == 'time':
                # Daily at specific time
                schedule.every().day.at(parsed_schedule).do(
                    self.execute_scheduled_task, schedule_data
                ).tag(f"schedule_{schedule_id}")
                logger.info(f"Scheduled daily task at {parsed_schedule}")
                
            elif schedule_type == 'interval':
                # Interval-based scheduling
                interval_value, unit = parsed_schedule.split('_')
                interval_value = int(interval_value)
                
                if unit == 'minutes':
                    schedule.every(interval_value).minutes.do(
                        self.execute_scheduled_task, schedule_data
                    ).tag(f"schedule_{schedule_id}")
                elif unit == 'hours':
                    schedule.every(interval_value).hours.do(
                        self.execute_scheduled_task, schedule_data
                    ).tag(f"schedule_{schedule_id}")
                elif unit == 'days':
                    schedule.every(interval_value).days.do(
                        self.execute_scheduled_task, schedule_data
                    ).tag(f"schedule_{schedule_id}")
                    
                logger.info(f"Scheduled interval task every {interval_value} {unit}")
                
            elif schedule_type == 'weekly':
                # Weekly scheduling
                day, time_part = parsed_schedule.split('_')
                
                day_map = {
                    'monday': schedule.every().monday,
                    'tuesday': schedule.every().tuesday,
                    'wednesday': schedule.every().wednesday,
                    'thursday': schedule.every().thursday,
                    'friday': schedule.every().friday,
                    'saturday': schedule.every().saturday,
                    'sunday': schedule.every().sunday
                }
                
                if day in day_map:
                    day_map[day].at(time_part).do(
                        self.execute_scheduled_task, schedule_data
                    ).tag(f"schedule_{schedule_id}")
                    logger.info(f"Scheduled weekly task on {day} at {time_part}")
                else:
                    logger.error(f"Invalid day: {day}")
                    
        except Exception as e:
            logger.error(f"Error setting up schedule {schedule_id}: {e}")
    
    def load_schedules(self):
        """Load all schedules from Supabase and set them up."""
        logger.info("Loading schedules from Supabase")
        
        # Clear existing schedules
        schedule.clear()
        self.schedules_cache.clear()
        
        # Fetch and set up new schedules
        schedules = self.fetch_schedules()
        for schedule_data in schedules:
            schedule_id = schedule_data.get('id')
            self.schedules_cache[schedule_id] = schedule_data
            self.setup_schedule(schedule_data)
        
        logger.info(f"Loaded {len(schedules)} schedules")
    
    def reload_schedules(self):
        """Reload schedules from database (can be called periodically)."""
        logger.info("Reloading schedules from database")
        self.load_schedules()
    
    def _scheduler_worker(self):
        """Worker thread that runs the scheduler."""
        logger.info("Scheduler worker thread started")
        
        # Initial load of schedules
        self.load_schedules()
        
        # Schedule periodic reload of schedules (every 5 minutes)
        schedule.every(5).minutes.do(self.reload_schedules)
        
        while self.running:
            try:
                # Run pending scheduled tasks
                schedule.run_pending()
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in scheduler worker: {e}")
                time.sleep(5)  # Wait a bit before retrying
        
        logger.info("Scheduler worker thread stopped")
    
    def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return False
        
        logger.info("Starting task scheduler")
        self.running = True
        
        # Start the scheduler worker thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_worker)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info("Task scheduler started")
        return True
    
    def stop(self):
        """Stop the scheduler."""
        if not self.running:
            logger.debug("Scheduler already stopped")
            return
        
        logger.info("Stopping task scheduler")
        self.running = False
        
        # Clear all scheduled jobs
        schedule.clear()
        
        # Wait for scheduler thread to finish
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        logger.info("Task scheduler stopped")
    
    def get_scheduled_jobs(self) -> List[Dict]:
        """Get information about currently scheduled jobs."""
        jobs_info = []
        for job in schedule.get_jobs():
            job_info = {
                'job': str(job),
                'next_run': job.next_run.isoformat() if job.next_run else None,
                'tags': list(job.tags) if job.tags else []
            }
            jobs_info.append(job_info)
        return jobs_info
    
    def get_status(self) -> Dict:
        """Get scheduler status information."""
        return {
            'running': self.running,
            'cached_schedules': len(self.schedules_cache),
            'active_jobs': len(schedule.get_jobs()),
            'jobs': self.get_scheduled_jobs()
        }