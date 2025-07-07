"""Log publisher to Supabase for all log files in logs/ directory."""

import os
import time
import threading
import json
from supabase import create_client
from config import LOG_DIRECTORY, SUPABASE_URL, SUPABASE_KEY, ID

# Table name and eraserId
TABLE_NAME = "EraserLogs"
ERASER_ID = ID

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Track file positions to only read new lines
def tail_filenames(log_dir):
    """Yield (filename, file object) for each log file in directory."""
    for fname in os.listdir(log_dir):
        if fname.endswith('.log'):
            yield fname, open(os.path.join(log_dir, fname), 'r', encoding='utf-8', errors='ignore')

def publish_log_line(filename, line):
    """Publish a log line to Supabase with file prefix."""
    message = f"[{filename}] {line.strip()}"
    try:
        supabase.table(TABLE_NAME).insert({
            "eraserId": ERASER_ID,
            "message": message
        }).execute()
    except Exception as e:
        print(f"Failed to publish log: {e}")

STATE_FILE = os.path.join(LOG_DIRECTORY, ".log_publisher_state.json")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Failed to save state: {e}")

def monitor_logs():
    """Continuously monitor all log files and publish new lines, starting from the last published position."""
    log_files = {fname: f for fname, f in tail_filenames(LOG_DIRECTORY)}
    state = load_state()  # {filename: position}
    # Seek to last published position for each file
    for fname, f in log_files.items():
        pos = state.get(fname, 0)
        try:
            f.seek(pos)
        except Exception:
            f.seek(0)
    while True:
        updated = False
        for fname, f in log_files.items():
            while True:
                where = f.tell()
                line = f.readline()
                if not line:
                    f.seek(where)
                    break
                publish_log_line(fname, line)
                state[fname] = f.tell()
                updated = True
        if updated:
            save_state(state)
        time.sleep(0.5)

def main():
    print("Starting log publisher to Supabase...")
    monitor_logs()

if __name__ == "__main__":
    main()
